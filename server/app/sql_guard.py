import re

from app.config_loader import load_data_catalog
from app.models.schemas import SqlValidationResult


DANGEROUS_PATTERNS = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\btruncate\b",
    r"\bcreate\b",
    r"\breplace\b",
    r"\bmerge\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcall\b",
    r"\bexec(?:ute)?\b",
    r"\bload\b",
    r"\boutfile\b",
    r"\bdumpfile\b",
    r"\binto\s+file\b",
    r"\bset\b",
    r"\buse\b",
]


TABLE_PATTERN = re.compile(r"\b(?:from|join)\s+([`\"\[]?[a-zA-Z_][\w$]*(?:[`\"\]]?\.[`\"\[]?[a-zA-Z_][\w$]*)?`?)", re.IGNORECASE)


def allowed_tables() -> list[str]:
    catalog = load_data_catalog()
    tables = []
    for asset in catalog.get("assets", []):
        table = asset.get("table")
        if table:
            tables.append(normalize_table_name(table))
    return sorted(set(tables))


def validate_sql(sql: str) -> SqlValidationResult:
    normalized_sql = sql.strip()
    allowed = allowed_tables()
    errors: list[str] = []
    warnings: list[str] = []

    if not normalized_sql:
        errors.append("SQL 不能为空。")

    if has_multiple_statements(normalized_sql):
        errors.append("只允许单条 SQL 语句。")

    if not starts_with_select(normalized_sql):
        errors.append("只允许 SELECT 查询。")

    lowered = strip_string_literals(normalized_sql).lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, lowered):
            errors.append(f"检测到禁止的 SQL 关键字或模式：{pattern}")

    tables = extract_tables(normalized_sql)
    if not tables:
        warnings.append("未识别到 FROM/JOIN 表名，请确认 SQL 是否完整。")

    blocked = [table for table in tables if table not in allowed]
    if blocked:
        errors.append(f"查询表不在 allowed tables 中：{', '.join(blocked)}")

    return SqlValidationResult(
        valid=not errors,
        sql=normalized_sql,
        tables=tables,
        allowed_tables=allowed,
        errors=errors,
        warnings=warnings,
    )


def starts_with_select(sql: str) -> bool:
    return bool(re.match(r"^\s*select\b", sql, re.IGNORECASE))


def has_multiple_statements(sql: str) -> bool:
    stripped = sql.rstrip()
    if stripped.endswith(";"):
        stripped = stripped[:-1]
    return ";" in strip_string_literals(stripped)


def extract_tables(sql: str) -> list[str]:
    tables = []
    for match in TABLE_PATTERN.finditer(sql):
        table = normalize_table_name(match.group(1))
        if table:
            tables.append(table)
    return sorted(set(tables))


def normalize_table_name(table: str) -> str:
    table = table.strip().strip("`[]\"")
    if "." in table:
        table = table.split(".")[-1]
    return table.strip("`[]\"").lower()


def strip_string_literals(sql: str) -> str:
    return re.sub(r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\")", "''", sql)
