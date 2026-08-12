"""Small, testable hand-rolled multi-provider tool loop."""
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any
from app.agents.providers import ProviderClient
from app.agents.system_prompt import SYSTEM_PROMPT
from app.core.memory import SessionMemory
from app.tools.registry import ToolDefinition, anthropic_tools

logger = logging.getLogger(__name__)


class InsightForgeAgent:
    """Coordinates one provider and five flat tools while emitting UI-friendly SSE payloads."""
    def __init__(self, client: ProviderClient, registry: dict[str, ToolDefinition], memory: SessionMemory, model: str, provider: str = "LLM") -> None:
        self.client, self.registry, self.memory, self.model = client, registry, memory, model
        self.provider = provider

    async def run(self, session_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
        state = await self.memory.get(session_id)
        conversational_reply = self._conversational_reply(message)
        if conversational_reply:
            state["history"] = (state["history"] + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": conversational_reply},
            ])[-12:]
            await self.memory.save(session_id, state)
            yield {"event": "token", "data": {"text": conversational_reply}}
            yield {"event": "done", "data": {"session_id": session_id}}
            return
        unavailable_year_reply = await self._unavailable_year_reply(message)
        if unavailable_year_reply:
            state["history"] = (state["history"] + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": unavailable_year_reply},
            ])[-12:]
            state.setdefault("query_history", []).append({"question": message, "summary": unavailable_year_reply})
            state["query_history"] = state["query_history"][-20:]
            await self.memory.save(session_id, state)
            yield {"event": "token", "data": {"text": unavailable_year_reply}}
            yield {"event": "suggestions", "data": {"actions": self._no_data_actions()}}
            yield {"event": "done", "data": {"session_id": session_id}}
            return
        messages: list[dict[str, Any]] = state["history"][-12:] + [{"role": "user", "content": message}]
        retries = 0
        for _ in range(8):
            try:
                response = await self.client.create(
                    model=self.model, max_tokens=1024, system=SYSTEM_PROMPT,
                    tools=anthropic_tools(self.registry), messages=messages,
                )
            except Exception as exc:
                logger.warning("%s provider request failed: %s", self.provider, self._provider_log_detail(exc))
                async for event in self._provider_fallback(message, exc):
                    yield event
                state["history"] = messages[-12:]
                await self.memory.save(session_id, state)
                yield {"event": "done", "data": {"session_id": session_id}}
                return
            content = self._content(response)
            tool_blocks = [block for block in content if self._kind(block) == "tool_use"]
            text_blocks = [self._text(block) for block in content if self._kind(block) == "text" and self._text(block)]
            for token in text_blocks:
                yield {"event": "token", "data": {"text": token}}
            if not tool_blocks:
                messages.append({"role": "assistant", "content": content})
                state["history"] = messages[-12:]
                state["query_history"].append({"question": message, "summary": "".join(text_blocks)[:500]})
                state["query_history"] = state["query_history"][-20:]
                await self.memory.save(session_id, state)
                yield {"event": "done", "data": {"session_id": session_id}}
                return
            messages.append({"role": "assistant", "content": content})
            results: list[dict[str, Any]] = []
            retry_needed = False
            latest_tool_error: dict[str, Any] | None = None
            for block in tool_blocks:
                name, tool_id, tool_input = self._name(block), self._id(block), self._input(block)
                # Result rows stay server-side.  Asking a model to copy a large result
                # set into a second tool call is error-prone and can corrupt the call.
                if name == "generate_chart":
                    tool_input = {**tool_input, "data": state.get("last_result", {}).get("rows", [])}
                if name == "explain_data":
                    tool_input = {**tool_input, "query_results": state.get("last_result", {})}
                yield {"event": "tool_call", "data": {"name": name, "input": tool_input}}
                tool = self.registry.get(name)
                if tool is None:
                    result = {"error": True, "message": f"Unknown tool {name}", "recoverable": False}
                else:
                    try:
                        result = await tool.handler(tool.input_model.model_validate(tool_input))
                    except Exception as exc:
                        result = {"error": True, "message": f"Invalid input for {name}: {exc}", "recoverable": True}
                if result.get("error") and result.get("recoverable"):
                    retry_needed = True
                    latest_tool_error = result
                if name == "execute_query" and not result.get("error"):
                    state["last_result"] = result
                    yield {"event": "sql", "data": {"sql": result.get("sql", tool_input.get("sql", ""))}}
                    yield {"event": "table", "data": {key: result.get(key) for key in ("columns", "rows", "row_count", "truncated")}}
                if name == "generate_chart" and not result.get("error"):
                    yield {"event": "chart", "data": result}
                if name == "generate_flowchart" and not result.get("error"):
                    yield {"event": "diagram", "data": result}
                yield {"event": "tool_result", "data": {"name": name, "result": result}}
                # Do not let an invalid SQL attempt turn into a broader, unrelated query.
                if name == "execute_query" and result.get("error"):
                    reply = self._tool_failure_reply(message, result)
                    state["history"] = (state["history"] + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": reply},
                    ])[-12:]
                    state.setdefault("query_history", []).append({"question": message, "summary": reply})
                    state["query_history"] = state["query_history"][-20:]
                    await self.memory.save(session_id, state)
                    yield {"event": "token", "data": {"text": reply}}
                    yield {"event": "suggestions", "data": {"actions": self._data_actions()}}
                    yield {"event": "done", "data": {"session_id": session_id}}
                    return
                result_for_model = result
                if name == "execute_query" and not result.get("error"):
                    result_for_model = {
                        key: result.get(key)
                        for key in ("columns", "row_count", "truncated", "sql")
                    }
                    result_for_model["sample_rows"] = result.get("rows", [])[:20]
                    result_for_model["note"] = "Use only the listed columns when choosing chart fields; the application supplies full result rows to chart and explanation tools."
                results.append({"type": "tool_result", "tool_use_id": tool_id, "tool_name": name, "content": json.dumps(result_for_model, default=str), "is_error": bool(result.get("error"))})
                if name == "execute_query" and not result.get("error") and result.get("row_count", 0) == 0:
                    reply = self._no_data_reply(message)
                    state["history"] = (state["history"] + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": reply},
                    ])[-12:]
                    state.setdefault("query_history", []).append({"question": message, "summary": reply})
                    state["query_history"] = state["query_history"][-20:]
                    await self.memory.save(session_id, state)
                    yield {"event": "token", "data": {"text": reply}}
                    yield {"event": "suggestions", "data": {"actions": self._no_data_actions()}}
                    yield {"event": "done", "data": {"session_id": session_id}}
                    return
            messages.append({"role": "user", "content": results})
            if retry_needed:
                if retries >= 1:
                    reply = self._tool_failure_reply(message, latest_tool_error)
                    state["history"] = (state["history"] + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": reply},
                    ])[-12:]
                    await self.memory.save(session_id, state)
                    yield {"event": "token", "data": {"text": reply}}
                    yield {"event": "suggestions", "data": {"actions": self._data_actions()}}
                    yield {"event": "done", "data": {"session_id": session_id}}
                    return
                retries += 1
        reply = "I reached the safe analysis limit before I could produce a reliable answer. Please try a more specific question, such as a single metric, date range, or table."
        yield {"event": "token", "data": {"text": reply}}
        yield {"event": "suggestions", "data": {"actions": self._data_actions()}}
        yield {"event": "done", "data": {"session_id": session_id}}

    async def _provider_fallback(self, message: str, error: Exception) -> AsyncIterator[dict[str, Any]]:
        """Run reviewed offline analyses during an AI-provider outage.

        Free-form text-to-SQL remains disabled here. Requests outside this small,
        safe set receive a clear explanation instead of a blank or fabricated answer.
        """
        question = message.lower()
        provider_reason = self._provider_error(error)
        query: tuple[str, str, str, str, str] | None = None

        if "monthly" in question and "revenue" in question:
            year_match = re.search(r"\b(20\d{2})\b", question)
            year = year_match.group(1) if year_match else None
            where = f"WHERE strftime('%Y', sale_date) = '{year}'" if year else ""
            query = (f"SELECT strftime('%Y-%m', sale_date) AS month, ROUND(SUM(revenue), 2) AS revenue FROM sales {where} GROUP BY month ORDER BY month", "Monthly revenue trend" + (f" for {year}" if year else ""), "line", "month", "revenue")
        elif "revenue" in question and ("category" in question or "categories" in question):
            query = ("SELECT c.name AS category, ROUND(SUM(s.revenue), 2) AS revenue FROM sales s JOIN products p ON p.id = s.product_id JOIN categories c ON c.id = p.category_id GROUP BY c.name ORDER BY revenue DESC", "Revenue by category", "pie" if "pie" in question or "distribution" in question else "bar", "category", "revenue")
        elif "customer" in question and ("tier" in question or "distribution" in question):
            query = ("SELECT tier, COUNT(*) AS customers FROM customers GROUP BY tier ORDER BY customers DESC", "Customers by tier", "pie" if "pie" in question or "distribution" in question else "bar", "tier", "customers")
        elif "city" in question and ("customer" in question or "cities" in question):
            query = ("SELECT city, COUNT(*) AS customers FROM customers GROUP BY city ORDER BY customers DESC", "Customers by city", "bar", "city", "customers")
        elif "salary" in question and "department" in question:
            query = ("SELECT department, ROUND(AVG(salary), 2) AS average_salary FROM employees GROUP BY department ORDER BY average_salary DESC", "Average salary by department", "bar", "department", "average_salary")
        elif "employee" in question and "department" in question:
            query = ("SELECT department, COUNT(*) AS employees FROM employees GROUP BY department ORDER BY employees DESC", "Employee count by department", "bar", "department", "employees")
        elif "payment method" in question:
            query = ("SELECT payment_method, COUNT(*) AS orders FROM orders GROUP BY payment_method ORDER BY orders DESC", "Orders by payment method", "pie" if "pie" in question or "distribution" in question else "bar", "payment_method", "orders")
        elif "low" in question and ("stock" in question or "inventory" in question):
            query = ("SELECT name AS product, stock_quantity FROM products ORDER BY stock_quantity ASC LIMIT 10", "Products with the lowest stock", "bar", "product", "stock_quantity")
        elif "rating" in question and "category" in question:
            query = ("SELECT c.name AS category, ROUND(AVG(p.rating), 2) AS average_rating FROM products p JOIN categories c ON c.id = p.category_id GROUP BY c.name ORDER BY average_rating DESC", "Average product rating by category", "bar", "category", "average_rating")

        if "er diagram" in question or ("database" in question and "diagram" in question):
            schema_tool = self.registry["get_schema"]
            schema = await schema_tool.handler(schema_tool.input_model())
            diagram_tool = self.registry["generate_flowchart"]
            diagram = await diagram_tool.handler(diagram_tool.input_model(diagram_type="er", context=schema))
            if not diagram.get("error"):
                yield {"event": "diagram", "data": diagram}
                yield {"event": "token", "data": {"text": f"{provider_reason} I generated this ER diagram directly from the live database schema instead."}}
                return

        if query:
            sql, title, chart_type, x_field, y_field = query
            execute_tool = self.registry["execute_query"]
            result = await execute_tool.handler(execute_tool.input_model(sql=sql))
            if not result.get("error"):
                yield {"event": "sql", "data": {"sql": result["sql"]}}
                yield {"event": "table", "data": {key: result.get(key) for key in ("columns", "rows", "row_count", "truncated")}}
                if result.get("row_count", 0) == 0:
                    yield {"event": "token", "data": {"text": self._no_data_reply(message)}}
                    yield {"event": "suggestions", "data": {"actions": self._no_data_actions()}}
                    return
                chart_tool = self.registry["generate_chart"]
                chart = await chart_tool.handler(chart_tool.input_model(chart_type=chart_type, data=result["rows"], x_field=x_field, y_field=y_field, title=title))
                if not chart.get("error"):
                    yield {"event": "chart", "data": chart}
                yield {"event": "token", "data": {"text": f"{provider_reason} {self._offline_result_summary(title, result['rows'], x_field, y_field)}"}}
                return

        yield {"event": "token", "data": {"text": f"{provider_reason} I could not complete a live database analysis for that request. I will not guess or invent an answer. This workspace contains products, customers, orders, sales, reviews, employees, and categories. Try one of the suggested analyses, or ask about a field in those tables."}}
        yield {"event": "suggestions", "data": {"actions": self._data_actions()}}

    @staticmethod
    def _conversational_reply(message: str) -> str | None:
        """Keep greetings and simple conversation out of the SQL agent loop."""
        normalized = " ".join("".join(char if char.isalnum() or char.isspace() else " " for char in message.lower()).split())
        if not normalized:
            return "Hello! Ask me anything about your database when you're ready."
        words = normalized.split()
        analytics_words = {
            "sales", "sale", "revenue", "customer", "customers", "product", "products", "order", "orders", "chart", "database", "sql", "employee", "employees", "category", "categories", "review", "reviews", "stock", "inventory", "rating", "payment", "salary", "department", "table", "tables", "column", "columns", "record", "records", "count", "total", "average", "highest", "lowest", "top", "compare", "trend", "month", "year", "date",
        }
        if normalized in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "hi mitra", "hello mitra"} or (words and words[0] in {"hi", "hello", "hey"} and not analytics_words.intersection(words)):
            return "Hello! I’m Mitra, your database analytics assistant. Ask me about sales, customers, products, orders, employees, or request a chart."
        if normalized in {"how are you", "how are you doing", "how are things"}:
            return "I’m doing well and ready to explore your data. What would you like to analyze?"
        if normalized in {"how was your day", "how is your day", "how has your day been", "how was your day mitra"}:
            return "I do not experience days like a person, but I am online, ready to help, and glad you asked. What would you like to explore?"
        if normalized in {"thanks", "thank you", "thank you so much", "thanks mitra"}:
            return "You’re welcome! Let me know whenever you’d like another analysis."
        if normalized in {"bye", "goodbye", "see you", "see you later"}:
            return "Goodbye! Your recent conversations will remain available here for the next seven days."
        if normalized in {"help", "what can you do", "what do you do", "how do you work", "what is the purpose of this chatbot", "what is the purpose of this chat bot", "what is this chatbot for", "what is mitra for", "why does this chatbot exist"}:
            return "I can turn database questions into safe SQL, show the returned records in a table, explain the result, and create charts. Try: “Show monthly revenue for 2025” or “Which city has the most customers?”"
        if normalized in {"who are you", "what is your name", "whats your name"}:
            return "I’m Mitra, your database analytics assistant."
        unsupported_entities = {
            "supplier", "suppliers", "vendor", "vendors", "shipment", "shipments",
            "shipping", "delivery", "deliveries", "warehouse", "warehouses",
        }
        if unsupported_entities.intersection(words):
            return "This connected database does not include supplier, shipment, delivery, vendor, or warehouse data. I can analyze categories, products, customers, orders, sales, reviews, and employees instead."
        if not analytics_words.intersection(words):
            return "I am happy to chat, but I do not have personal experiences or live information outside this workspace. I can help you explore the connected database, explain what data is available, or answer casual questions about how I work."
        return None

    async def _unavailable_year_reply(self, message: str) -> str | None:
        """Answer impossible year filters from live data before an LLM can broaden them."""
        years = re.findall(r"\b(20\d{2})\b", message)
        if not years:
            return None
        question = message.lower()
        source: tuple[str, str] | None = None
        if any(word in question for word in ("sale", "sales", "revenue", "quantity")):
            source = ("sales", "sale_date")
        elif "order" in question:
            source = ("orders", "order_date")
        if source is None:
            return None
        table, date_column = source
        tool = self.registry["execute_query"]
        result = await tool.handler(tool.input_model(sql=(
            f"SELECT MIN(strftime('%Y', {date_column})) AS first_year, "
            f"MAX(strftime('%Y', {date_column})) AS last_year FROM {table}"
        )))
        if result.get("error") or not result.get("rows"):
            return None
        available = result["rows"][0]
        first_year, last_year = available.get("first_year"), available.get("last_year")
        requested = years[-1]
        if first_year and last_year and not (str(first_year) <= requested <= str(last_year)):
            return f"There is no {table} data for {requested}. The connected {table} data covers {first_year} to {last_year}, so I cannot provide a reliable answer for that year. Try a date within that range or ask for the available date range."
        return None

    @staticmethod
    def _conversation_actions() -> list[dict[str, str]]:
        return [
            {"label": "What can you analyze?", "prompt": "What can you analyze in this database?"},
            {"label": "Show available tables", "prompt": "Show the available tables and their purpose"},
            {"label": "Show revenue trend", "prompt": "Show monthly revenue trend for 2025"},
        ]

    @staticmethod
    def _data_actions() -> list[dict[str, str]]:
        return [
            {"label": "Show available tables", "prompt": "Show the available tables and their purpose"},
            {"label": "Revenue by category", "prompt": "Show revenue by category as a bar chart"},
            {"label": "Customers by city", "prompt": "Which cities have the most customers?"},
        ]

    @staticmethod
    def _no_data_actions() -> list[dict[str, str]]:
        return [
            {"label": "Show available date range", "prompt": "What is the available date range in the sales and orders data?"},
            {"label": "Show available tables", "prompt": "Show the available tables and their purpose"},
            {"label": "Try revenue by category", "prompt": "Show revenue by category as a bar chart"},
        ]

    @staticmethod
    def _no_data_reply(message: str) -> str:
        return f"I ran the database query for '{message}', but it returned no matching records. The requested data may not exist for those filters or date range. I have not created a chart because there are no rows to visualize. Try broadening the filters, choosing a different period, or inspecting the available fields."

    @staticmethod
    def _offline_result_summary(title: str, rows: list[dict[str, Any]], x_field: str, y_field: str) -> str:
        """Give a grounded answer when the reviewed offline analysis handled the query."""
        numeric_rows = [row for row in rows if isinstance(row.get(y_field), (int, float)) and not isinstance(row.get(y_field), bool)]
        if not numeric_rows:
            return f"I ran the built-in, read-only analysis for {title.lower()} and found {len(rows)} result(s)."
        highest = max(numeric_rows, key=lambda row: row[y_field])
        lowest = min(numeric_rows, key=lambda row: row[y_field])
        if len(numeric_rows) == 1:
            return f"I ran the built-in, read-only analysis for {title.lower()}. {highest.get(x_field)} is {highest[y_field]:,.2f}."
        return (
            f"I ran the built-in, read-only analysis for {title.lower()}. "
            f"The highest value is {highest[y_field]:,.2f} for {highest.get(x_field)}, "
            f"and the lowest is {lowest[y_field]:,.2f} for {lowest.get(x_field)}."
        )

    @staticmethod
    def _tool_failure_reply(message: str, error: dict[str, Any] | None) -> str:
        detail = str((error or {}).get("message", "")).lower()
        if "no such column" in detail or "no such table" in detail or "unknown column" in detail:
            return f"I could not find one of the requested fields in the database while analyzing '{message}'. This database may not track that metric or entity. I have not guessed a result; use the available-table suggestion to choose a related field."
        return f"I could not safely complete the database query for '{message}'. I stopped before returning an unreliable answer. Try a more specific question or choose one of the related analyses below."

    @staticmethod
    def _field(value: Any, name: str, default: Any = None) -> Any:
        """Read from Anthropic SDK objects or light-weight dict mocks without eager defaults."""
        return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)

    @classmethod
    def _content(cls, response: Any) -> list[Any]: return list(cls._field(response, "content", []))
    @classmethod
    def _kind(cls, block: Any) -> str: return cls._field(block, "type")
    @classmethod
    def _text(cls, block: Any) -> str: return cls._field(block, "text", "")
    @classmethod
    def _name(cls, block: Any) -> str: return cls._field(block, "name")
    @classmethod
    def _id(cls, block: Any) -> str: return cls._field(block, "id")
    @classmethod
    def _input(cls, block: Any) -> dict[str, Any]: return cls._field(block, "input", {})

    def _provider_error(self, error: Exception) -> str:
        """Convert upstream errors into actionable messages without exposing request IDs."""
        detail = str(error).lower()
        name = self.provider.title()
        failures = getattr(error, "failures", [])
        if hasattr(error, "failures") and not failures:
            return "No usable AI provider key is configured."
        if failures:
            failed_provider, failed_error = failures[0]
            name = str(failed_provider).title()
            detail = str(failed_error).lower()
        if "401" in detail or "authentication" in detail or "invalid api key" in detail or "invalid x-api-key" in detail:
            return f"{name} rejected this API key. Select the matching provider and paste a valid key, or update the corresponding server environment variable."
        if "429" in detail or "rate limit" in detail or "quota" in detail:
            return f"{name} is rate-limiting this request or the account has no remaining quota. Try again shortly or select another provider."
        if "403" in detail or "permission" in detail or "forbidden" in detail:
            return f"This {name} key does not have permission to use the selected model. Check its project/model permissions or select another model."
        if "400" in detail or "invalid request" in detail or "bad request" in detail:
            return f"{name} rejected the request format. Try the provider’s suggested model; the server terminal contains the detailed provider response."
        if "404" in detail or "not found" in detail or "model" in detail:
            return f"The selected {name} model is unavailable for this key. Choose a model available in that provider account."
        return f"{name} could not complete the request. Check the provider key, model name, and server terminal for details."

    @staticmethod
    def _provider_log_detail(error: Exception) -> str:
        """Keep the exact provider failure in server logs without sending it to the browser."""
        failures = getattr(error, "failures", [])
        if failures:
            return "; ".join(f"{name}: {type(exc).__name__}: {exc}" for name, exc in failures)
        return f"{type(error).__name__}: {error}"
