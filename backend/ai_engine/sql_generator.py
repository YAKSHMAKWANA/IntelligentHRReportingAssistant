from ai_engine.ollama_client import ask_ollama


def generate_sql(question, knowledge):
    """
    Generate a safe MySQL SELECT query from the user's
    natural-language HR request and retrieved HR knowledge.
    """

    context = ""

    # -------------------------------------------------
    # RETRIEVED HR REPORTS
    # -------------------------------------------------

    if knowledge["reports"]:
        for report in knowledge["reports"]:
            context += f"""
REPORT:
Name: {report.name}
Description: {report.description}
Category: {report.category}

EXISTING SQL:
{report.sql_query}

----------------------------------------
"""
    else:
        context += """
No specific HR report was retrieved.
Use only the provided database schema.
"""

    # -------------------------------------------------
    # BUSINESS RULES
    # -------------------------------------------------

    if knowledge["business_rules"]:
        for rule in knowledge["business_rules"]:
            context += f"""
BUSINESS RULE:
Name: {rule.name}
Description: {rule.description}
Rule:
{rule.rule_text}

----------------------------------------
"""

    # -------------------------------------------------
    # SECURITY RULES
    # -------------------------------------------------

    if knowledge["security_rules"]:
        for rule in knowledge["security_rules"]:
            context += f"""
SECURITY RULE:
Name: {rule.name}
Description: {rule.description}
Allowed Roles:
{rule.allowed_roles}
Rule:
{rule.rule_text}

----------------------------------------
"""

    # -------------------------------------------------
    # AI PROMPT
    # -------------------------------------------------

    prompt = f"""
You are an intelligent HR reporting SQL assistant.

Your task is to convert the user's natural-language HR
request into ONE safe MySQL SELECT query.

USER REQUEST:
{question}

RETRIEVED HR KNOWLEDGE:
{context}

==================================================
DATABASE SCHEMA
==================================================

reports_department

Columns:
- id
- name
- description


reports_employee

Columns:
- id
- employee_id
- first_name
- last_name
- email
- department_id
- job_title
- hire_date
- status
- effective_start_date
- effective_end_date
- created_at
- updated_at


==================================================
VALID EMPLOYEE STATUS VALUES
==================================================

ACTIVE
ON_LEAVE
INACTIVE


==================================================
MANDATORY CONDITION RULE
==================================================

EVERY condition explicitly requested by the user MUST
appear in the final SQL.

Never remove a condition because another condition
was also requested.

For example:

USER:
Who was active on 2026-01-01?

The query MUST contain BOTH:

e.status = 'ACTIVE'

AND the historical effective-date condition:

e.effective_start_date <= '2026-01-01'

AND:

(
    e.effective_end_date IS NULL
    OR e.effective_end_date >= '2026-01-01'
)


==================================================
STATUS RULES
==================================================

If the user asks for ACTIVE employees:

e.status = 'ACTIVE'


If the user asks for employees ON LEAVE:

e.status = 'ON_LEAVE'


If the user asks for INACTIVE employees:

e.status = 'INACTIVE'


If the user asks about employee status without
specifying a status, do NOT assume ACTIVE.

Return all relevant statuses.


==================================================
CURRENT DATE RULE
==================================================

If the user asks about CURRENT employees, use:

e.effective_start_date <= CURRENT_DATE

AND:

(
    e.effective_end_date IS NULL
    OR e.effective_end_date >= CURRENT_DATE
)


==================================================
HISTORICAL DATE RULE
==================================================

If the user provides a specific date, use that exact
date instead of CURRENT_DATE.

Example:

USER:
Who was active on 2026-01-01?

REQUIRED CONDITIONS:

e.status = 'ACTIVE'

AND:

e.effective_start_date <= '2026-01-01'

AND:

(
    e.effective_end_date IS NULL
    OR e.effective_end_date >= '2026-01-01'
)


Example:

USER:
Who was on leave on 2026-01-01?

REQUIRED CONDITIONS:

e.status = 'ON_LEAVE'

AND:

e.effective_start_date <= '2026-01-01'

AND:

(
    e.effective_end_date IS NULL
    OR e.effective_end_date >= '2026-01-01'
)


==================================================
DEPARTMENT RULE
==================================================

If the user specifies a department, the query MUST
join the department table.

Use:

JOIN reports_department d
ON e.department_id = d.id

Then use:

d.name = '<department>'


Example:

USER:
Show active employees in IT

REQUIRED:

e.status = 'ACTIVE'

AND:

d.name = 'IT'


Example:

USER:
Show active employees in IT on 2026-01-01

REQUIRED:

e.status = 'ACTIVE'

AND:

d.name = 'IT'

AND:

e.effective_start_date <= '2026-01-01'

AND:

(
    e.effective_end_date IS NULL
    OR e.effective_end_date >= '2026-01-01'
)


==================================================
JOB TITLE RULE
==================================================

If the user specifies a job title, filter using:

e.job_title

Example:

Show active software developers in IT

Must include:

e.status = 'ACTIVE'

AND:

d.name = 'IT'

AND an appropriate e.job_title condition.


==================================================
HIRE DATE RULE
==================================================

If the user asks when employees were hired, or asks
for employees hired between dates, use:

e.hire_date

Do NOT use effective_start_date for hiring questions.

Example:

Employees hired between 2025-01-01 and 2025-12-31

Use a condition equivalent to:

e.hire_date BETWEEN '2025-01-01' AND '2025-12-31'


==================================================
MULTIPLE CONDITIONS
==================================================

If the user provides multiple conditions, ALL of them
must appear in the SQL.

Example:

Show active developers in IT on 2026-01-01

Required:

e.status = 'ACTIVE'

AND:

d.name = 'IT'

AND appropriate e.job_title condition

AND:

e.effective_start_date <= '2026-01-01'

AND:

(
    e.effective_end_date IS NULL
    OR e.effective_end_date >= '2026-01-01'
)


==================================================
EXISTING REPORTS
==================================================

Existing reports are authoritative sources of HR
reporting logic.

However, existing report SQL is only a TEMPLATE.

If the user asks for additional conditions, modify the
report SQL.

Never blindly copy an existing report if it does not
satisfy the complete request.


==================================================
CUSTOM REPORTS
==================================================

User-added reports are valid HR reporting knowledge.

Use their:

- name
- description
- category
- SQL

when relevant.

Do not assume only built-in reports are valid.


==================================================
RESULT COLUMNS
==================================================

For employee reports, prefer:

e.employee_id
e.first_name
e.last_name
d.name AS department
e.job_title
e.status

Avoid SELECT *.


==================================================
SECURITY
==================================================

ONLY SELECT statements are allowed.

Never generate:

INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE

Never generate multiple SQL statements.

Never use SELECT INTO OUTFILE.

Never use LOAD_FILE().

Never modify the database.

==================================================
AGGREGATION RULES:
==================================================

1. If the user asks "how many", "count", "number of", or similar
   aggregation questions, generate COUNT() instead of returning
   individual employee rows.

2. If the user asks "how many employees are in each department",
   the SQL MUST use:

   COUNT(*) AS employee_count

   and:

   GROUP BY d.name

3. For "each department", return one row per department.

4. Do not return employee_id, first_name, last_name, or job_title
   when the user asks only for a count by department.

5. Example:

   SELECT
       d.name AS department,
       COUNT(*) AS employee_count
   FROM reports_employee e
   JOIN reports_department d
       ON e.department_id = d.id
   GROUP BY d.name;

6. Do not add ACTIVE status unless the user explicitly asks for
   active employees.

7. Do not add effective-date filters unless they are required by
   the user's question or the applicable HR business rule.


==================================================
TABLE RULES
==================================================

Use only:

reports_employee
reports_department

Do not invent tables.

Do not invent columns.


==================================================
FINAL VERIFICATION
==================================================

Before returning the SQL, verify each item:

1. Did I identify every condition?
2. Did I include the requested status?
3. Did I include the requested department?
4. Did I include the requested job title?
5. Did I include the requested historical date?
6. Did I use effective dating for a historical question?
7. Did I use hire_date for hiring questions?
8. Did I preserve relevant report logic?
9. Is this exactly ONE SELECT statement?
10. Did I avoid unsafe SQL?

If the user asks:

"Who was active on 2026-01-01?"

the final SQL MUST contain all three:

e.status = 'ACTIVE'

e.effective_start_date <= '2026-01-01'

e.effective_end_date IS NULL
OR
e.effective_end_date >= '2026-01-01'

Return ONLY the SQL query.

No explanation.
No Markdown.
No code fences.
"""

    # -------------------------------------------------
    # ASK OLLAMA
    # -------------------------------------------------

    sql = ask_ollama(prompt)

    sql = sql.strip()

    # -------------------------------------------------
    # CLEAN AI RESPONSE
    # -------------------------------------------------

    if sql.startswith("```sql"):
        sql = sql[6:]

    elif sql.startswith("```mysql"):
        sql = sql[8:]

    elif sql.startswith("```"):
        sql = sql[3:]

    if sql.endswith("```"):
        sql = sql[:-3]

    sql = sql.strip()

    return sql