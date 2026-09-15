import re


FORBIDDEN_COMMANDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
]


def validate_sql(sql):
    """
    Validate AI-generated SQL before execution.
    Only SELECT queries are allowed.
    """

    if not sql or not sql.strip():
        return False, "SQL query is empty."

    sql = sql.strip()

    # Only SELECT statements are allowed
    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # Reject multiple statements
    # This prevents something like:
    # SELECT ...; DROP TABLE ...
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]

    if len(statements) > 1:
        return False, "Multiple SQL statements are not allowed."

    # Reject dangerous SQL commands
    for command in FORBIDDEN_COMMANDS:
        pattern = r"\b" + re.escape(command) + r"\b"

        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Unsafe SQL command detected: {command}"

    return True, "SQL query is safe."