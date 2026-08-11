# InsightForge — 5-minute demo

## 0:00–0:30 — Problem

“Business data is locked behind SQL knowledge. InsightForge lets anyone ask a database a question, while still showing every generated query.” Open the chat at `localhost:5173`.

## 0:30–2:00 — Live question, SQL, chart, explanation

Ask: **“Show revenue by product.”** Point out the animated “Running SQL query…” status, expand **View generated SQL**, then ask **“Make that a bar chart.”** Call out the inline chart, CSV/PNG export, and the grounded explanation.

## 2:00–3:00 — Schema and follow-up context

Ask: **“Draw the database ER diagram.”** Highlight the reflected product/sales relationship. Then ask: **“Now show the trend for those products by month.”** Explain that the session retains prior tool results and conversation context in Redis for two hours.

## 3:00–4:00 — Dashboard bonus

Pin the chart, switch to **Dashboard**, and show that the saved view persists within the session. Mention query history is stored in the same session payload and can power rerun/favorite sidebar controls.

## 4:00–5:00 — Architecture

Show the README diagram. Emphasize one typed tool registry, one SQLAlchemy adapter boundary, SQLGlot AST safety, and an explicit Claude native-tool loop with a single correction retry.
