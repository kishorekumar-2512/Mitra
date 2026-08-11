"""AST-based SQL safety validation."""
from dataclasses import dataclass
import sqlglot
from sqlglot import exp

MAX_ROWS = 500


@dataclass(frozen=True)
class GuardedQuery:
    sql: str


def guard_read_only_sql(sql: str, dialect: str = "sqlite") -> GuardedQuery:
    """Accept exactly one SELECT-like AST and add a defensive row limit."""
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Invalid SQL: {exc}") from exc
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Subquery, exp.With)):
        raise ValueError("Only a single SELECT query is allowed.")
    expression = statements[0]
    if expression.find(exp.Insert) or expression.find(exp.Update) or expression.find(exp.Delete) or expression.find(exp.Drop) or expression.find(exp.Alter):
        raise ValueError("Write and schema-changing statements are prohibited.")
    existing_limit = expression.args.get("limit")
    if existing_limit is None:
        expression = expression.limit(MAX_ROWS + 1)
    else:
        limit_expression = existing_limit.expression
        try:
            if int(limit_expression.name) > MAX_ROWS + 1:
                expression = expression.limit(MAX_ROWS + 1)
        except (ValueError, TypeError):
            expression = expression.limit(MAX_ROWS + 1)
    return GuardedQuery(expression.sql(dialect=dialect))
