import re

from django.db import connection
from django.db.models import Q

from reports.models import Department, Employee, HRReport

from .ollama_client import ask_ollama
from .rag import retrieve_hr_knowledge
from .sql_validator import validate_sql


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_question(question):
    if not question:
        return ""

    question = str(question).strip()
    question = re.sub(r"\s+", " ", question)

    return question


def sql_escape(value):
    if value is None:
        return ""

    return str(value).replace("\\", "\\\\").replace("'", "''")


# ============================================================
# CONDITION EXTRACTION
# ============================================================

def extract_requested_conditions(question):
    """
    Extract filters from the user's natural-language question.

    Supports:
    - ACTIVE
    - INACTIVE
    - ON_LEAVE
    - department
    - job title
    - singular/plural job-title variations
    - exact hire date
    - hire date range
    - historical/effective date
    """

    question = clean_question(question)
    question_lower = question.lower()

    conditions = {
        "status": None,
        "department": None,
        "job_title": None,
        "hire_date": None,
        "hire_start_date": None,
        "hire_end_date": None,
        "historical_date": None,
    }

    # ========================================================
    # STATUS
    # ========================================================

    # IMPORTANT:
    # Check inactive before active because "active"
    # is contained inside "inactive".

    if re.search(r"\binactive\b", question_lower):

        conditions["status"] = "INACTIVE"

    elif re.search(r"\bon[\s_-]?leave\b", question_lower):

        conditions["status"] = "ON_LEAVE"

    elif re.search(r"\bactive\b", question_lower):

        conditions["status"] = "ACTIVE"

    # ========================================================
    # HIRE DATE RANGE
    # ========================================================

    range_patterns = [
        r"\bhired\s+between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})",
        r"\bjoined\s+between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})",
        r"\bhire\s+date\s+between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in range_patterns:

        match = re.search(
            pattern,
            question_lower
        )

        if match:

            conditions["hire_start_date"] = match.group(1)
            conditions["hire_end_date"] = match.group(2)

            break

    # ========================================================
    # EXACT HIRE DATE
    # ========================================================

    single_date_patterns = [
        r"\bhired\s+on\s+(\d{4}-\d{2}-\d{2})",
        r"\bjoined\s+on\s+(\d{4}-\d{2}-\d{2})",
        r"\bhire\s+date\s+(?:is|=)\s*(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in single_date_patterns:

        match = re.search(
            pattern,
            question_lower
        )

        if match:

            conditions["hire_date"] = match.group(1)

            break

    # ========================================================
    # HISTORICAL DATE
    # ========================================================

    historical_patterns = [
        r"\bas\s+of\s+(\d{4}-\d{2}-\d{2})",
        r"\bhistorical(?:\s+data)?\s+(?:for|on|as\s+of)\s+(\d{4}-\d{2}-\d{2})",
        r"\bat\s+the\s+end\s+of\s+(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in historical_patterns:

        match = re.search(
            pattern,
            question_lower
        )

        if match:

            conditions["historical_date"] = match.group(1)

            break

    # ========================================================
    # DEPARTMENT
    # ========================================================

    department_names = list(
        Department.objects.values_list(
            "name",
            flat=True
        )
    )

    department_names.sort(
        key=len,
        reverse=True
    )

    for department_name in department_names:

        if not department_name:
            continue

        department_name_clean = (
            department_name.strip().lower()
        )

        pattern = (
            r"(?<!\w)"
            + re.escape(department_name_clean)
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            question_lower
        ):

            conditions["department"] = department_name

            break

    # ========================================================
    # JOB TITLE
    # ========================================================

    job_titles = list(
        Employee.objects.values_list(
            "job_title",
            flat=True
        ).distinct()
    )

    job_titles = [
        title.strip()
        for title in job_titles
        if title and title.strip()
    ]

    job_titles.sort(
        key=len,
        reverse=True
    )

    for job_title in job_titles:

        title_lower = job_title.lower().strip()

        title_variants = [
            title_lower
        ]

        words = title_lower.split()

        if words:

            last_word = words[-1]

            # ------------------------------------------------
            # Normal plural
            # ------------------------------------------------

            if not last_word.endswith("s"):

                plural_last_word = (
                    last_word + "s"
                )

                plural_title = " ".join(
                    words[:-1]
                    + [plural_last_word]
                )

                title_variants.append(
                    plural_title
                )

            # ------------------------------------------------
            # y -> ies
            # ------------------------------------------------

            if (
                last_word.endswith("y")
                and len(last_word) > 1
                and last_word[-2] not in "aeiou"
            ):

                plural_last_word = (
                    last_word[:-1]
                    + "ies"
                )

                plural_title = " ".join(
                    words[:-1]
                    + [plural_last_word]
                )

                title_variants.append(
                    plural_title
                )

        matched = False

        for title_variant in title_variants:

            pattern = (
                r"(?<!\w)"
                + re.escape(title_variant)
                + r"(?!\w)"
            )

            if re.search(
                pattern,
                question_lower
            ):

                conditions["job_title"] = job_title

                matched = True

                break

        if matched:
            break

    return conditions


# ============================================================
# SELECT BUILDER
# ============================================================

def build_employee_select(include_status=False):

    columns = [
        "e.employee_id",
        "e.first_name",
        "e.last_name",
        "d.name AS department",
        "e.job_title",
    ]

    if include_status:

        columns.append(
            "e.status"
        )

    columns.append(
        "e.hire_date"
    )

    return ",\n    ".join(
        columns
    )


# ============================================================
# AGGREGATION DETECTION
# ============================================================

def detect_aggregation_request(question):

    question_lower = clean_question(
        question
    ).lower()

    aggregation_phrases = [
        "count",
        "how many",
        "how much",
        "number of",
        "total number",
        "total employees",
        "total employee",
        "total",
        "average",
        "avg",
        "maximum",
        "minimum",
        "max",
        "min",
        "most",
        "least",
        "fewest",
        "highest",
        "lowest",
        "per department",
        "by department",
        "each department",
        "department wise",
        "department-wise",
        "departmentwise",
        "per job title",
        "by job title",
        "each job title",
        "job title wise",
        "job-title-wise",
        "jobtitle wise",
        "different job title",
        "different job titles",
        "distinct job title",
        "distinct job titles",
        "unique job title",
        "unique job titles",
    ]

    return any(
        phrase in question_lower
        for phrase in aggregation_phrases
    )


def is_count_request(question):

    question_lower = clean_question(
        question
    ).lower()

    patterns = [
        r"\bhow many\b",
        r"\bcount\b",
        r"\bnumber of\b",
        r"\btotal number\b",
        r"\btotal employees\b",
        r"\btotal employee\b",
        r"\bhow much\b",
    ]

    return any(
        re.search(
            pattern,
            question_lower
        )
        for pattern in patterns
    )


def wants_group_by_department(question):

    question_lower = clean_question(
        question
    ).lower()

    patterns = [
        "by department",
        "per department",
        "each department",
        "department wise",
        "department-wise",
        "departmentwise",
    ]

    return any(
        phrase in question_lower
        for phrase in patterns
    )


def wants_group_by_job_title(question):

    question_lower = clean_question(
        question
    ).lower()

    patterns = [
        "by job title",
        "per job title",
        "each job title",
        "job title wise",
        "job-title-wise",
        "jobtitle wise",
    ]

    return any(
        phrase in question_lower
        for phrase in patterns
    )


def wants_distinct_job_title_count(question):

    question_lower = clean_question(
        question
    ).lower()

    patterns = [
        "different job title",
        "different job titles",
        "distinct job title",
        "distinct job titles",
        "unique job title",
        "unique job titles",
    ]

    return any(
        phrase in question_lower
        for phrase in patterns
    )


# ============================================================
# SQL CONDITION HELPERS
# ============================================================

def enforce_status(
    sql_parts,
    status,
    historical_date=None
):

    if not status:
        return

    status = sql_escape(
        status
    )

    sql_parts.append(
        "AND e.status = '{}'".format(
            status
        )
    )

    # Only ACTIVE employees need effective-date logic.

    if status != "ACTIVE":
        return

    # Historical ACTIVE query.

    if historical_date:

        historical_date = sql_escape(
            historical_date
        )

        sql_parts.append(
            "AND e.effective_start_date <= '{}'".format(
                historical_date
            )
        )

        sql_parts.append(
            "AND ("
            "e.effective_end_date IS NULL "
            "OR e.effective_end_date >= '{}'"
            ")".format(
                historical_date
            )
        )

    # Current ACTIVE query.

    else:

        sql_parts.append(
            "AND e.effective_start_date <= CURRENT_DATE"
        )

        sql_parts.append(
            "AND ("
            "e.effective_end_date IS NULL "
            "OR e.effective_end_date >= CURRENT_DATE"
            ")"
        )


def enforce_hire_date_range(
    sql_parts,
    hire_date=None,
    hire_start_date=None,
    hire_end_date=None
):

    if hire_date:

        sql_parts.append(
            "AND e.hire_date = '{}'".format(
                sql_escape(
                    hire_date
                )
            )
        )

    if hire_start_date:

        sql_parts.append(
            "AND e.hire_date >= '{}'".format(
                sql_escape(
                    hire_start_date
                )
            )
        )

    if hire_end_date:

        sql_parts.append(
            "AND e.hire_date <= '{}'".format(
                sql_escape(
                    hire_end_date
                )
            )
        )


def enforce_requested_conditions(
    sql_parts,
    conditions
):

    status = conditions.get(
        "status"
    )

    department = conditions.get(
        "department"
    )

    job_title = conditions.get(
        "job_title"
    )

    hire_date = conditions.get(
        "hire_date"
    )

    hire_start_date = conditions.get(
        "hire_start_date"
    )

    hire_end_date = conditions.get(
        "hire_end_date"
    )

    historical_date = conditions.get(
        "historical_date"
    )

    enforce_status(
        sql_parts,
        status,
        historical_date=historical_date
    )

    if department:

        sql_parts.append(
            "AND d.name = '{}'".format(
                sql_escape(
                    department
                )
            )
        )

    if job_title:

        sql_parts.append(
            "AND e.job_title = '{}'".format(
                sql_escape(
                    job_title
                )
            )
        )

    enforce_hire_date_range(
        sql_parts,
        hire_date=hire_date,
        hire_start_date=hire_start_date,
        hire_end_date=hire_end_date
    )


# ============================================================
# WHERE BUILDER
# ============================================================

def build_where_parts(
    conditions,
    dataset_id=None,
    include_department=True
):

    where_parts = []

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    if dataset_id is not None:

        where_parts.append(
            "e.dataset_id = {}".format(
                int(dataset_id)
            )
        )

    status = conditions.get(
        "status"
    )

    department = conditions.get(
        "department"
    )

    job_title = conditions.get(
        "job_title"
    )

    historical_date = conditions.get(
        "historical_date"
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if status:

        where_parts.append(
            "e.status = '{}'".format(
                sql_escape(
                    status
                )
            )
        )

        # ACTIVE requires effective dating.

        if status == "ACTIVE":

            if historical_date:

                historical_date = sql_escape(
                    historical_date
                )

                where_parts.append(
                    "e.effective_start_date <= '{}'".format(
                        historical_date
                    )
                )

                where_parts.append(
                    "("
                    "e.effective_end_date IS NULL "
                    "OR e.effective_end_date >= '{}'"
                    ")".format(
                        historical_date
                    )
                )

            else:

                where_parts.append(
                    "e.effective_start_date <= CURRENT_DATE"
                )

                where_parts.append(
                    "("
                    "e.effective_end_date IS NULL "
                    "OR e.effective_end_date >= CURRENT_DATE"
                    ")"
                )

    # --------------------------------------------------------
    # Department
    # --------------------------------------------------------

    if department and include_department:

        where_parts.append(
            "d.name = '{}'".format(
                sql_escape(
                    department
                )
            )
        )

    # --------------------------------------------------------
    # Job title
    # --------------------------------------------------------

    if job_title:

        where_parts.append(
            "e.job_title = '{}'".format(
                sql_escape(
                    job_title
                )
            )
        )

    # --------------------------------------------------------
    # Hire date
    # --------------------------------------------------------

    if conditions.get(
        "hire_date"
    ):

        where_parts.append(
            "e.hire_date = '{}'".format(
                sql_escape(
                    conditions["hire_date"]
                )
            )
        )

    if conditions.get(
        "hire_start_date"
    ):

        where_parts.append(
            "e.hire_date >= '{}'".format(
                sql_escape(
                    conditions["hire_start_date"]
                )
            )
        )

    if conditions.get(
        "hire_end_date"
    ):

        where_parts.append(
            "e.hire_date <= '{}'".format(
                sql_escape(
                    conditions["hire_end_date"]
                )
            )
        )

    return where_parts


def append_where(
    sql_parts,
    where_parts
):

    if where_parts:

        sql_parts.append(
            "WHERE "
            + "\n  AND ".join(
                where_parts
            )
        )


# ============================================================
# FAST SQL BUILDER
# ============================================================

def build_fast_hr_sql(
    question,
    dataset_id=None
):

    question = clean_question(
        question
    )

    if not question:
        return None

    question_lower = question.lower()

    conditions = extract_requested_conditions(
        question
    )

    status = conditions.get(
        "status"
    )

    department = conditions.get(
        "department"
    )

    job_title = conditions.get(
        "job_title"
    )

    # ========================================================
    # DISTINCT JOB TITLE COUNT
    # ========================================================

    if wants_distinct_job_title_count(
        question
    ):

        sql_parts = [
            "SELECT",
            "    COUNT(DISTINCT e.job_title) AS job_title_count",
            "FROM reports_employee e",
            "JOIN reports_department d",
            "    ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=True
        )

        append_where(
            sql_parts,
            where_parts
        )

        return "\n".join(
            sql_parts
        )

    # ========================================================
    # HIGHEST / MOST EMPLOYEES BY DEPARTMENT
    # ========================================================

    if (
        "most employees" in question_lower
        or "most employee" in question_lower
        or "department with the most" in question_lower
        or "department has the most" in question_lower
        or "largest department" in question_lower
        or "highest number of employees" in question_lower
        or "highest number of active employees" in question_lower
        or "highest number of inactive employees" in question_lower
        or "highest number of employees in" in question_lower
    ):

        sql_parts = [
            "SELECT",
            "    department,",
            "    employee_count",
            "FROM (",
            "    SELECT",
            "        d.name AS department,",
            "        COUNT(*) AS employee_count,",
            "        RANK() OVER (ORDER BY COUNT(*) DESC) AS ranking",
            "    FROM reports_employee e",
            "    JOIN reports_department d",
            "        ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=False
        )

        if where_parts:

            sql_parts.append(
                "    WHERE "
                + "\n      AND ".join(
                    where_parts
                )
            )

        sql_parts.extend([
            "    GROUP BY d.id, d.name",
            ") ranked_departments",
            "WHERE ranking = 1",
            "ORDER BY department ASC",
        ])

        return "\n".join(
            sql_parts
        )

    # ========================================================
    # LOWEST / FEWEST EMPLOYEES BY DEPARTMENT
    # ========================================================

    if (
        "fewest employees" in question_lower
        or "fewest employee" in question_lower
        or "department with the fewest" in question_lower
        or "department has the fewest" in question_lower
        or "smallest department" in question_lower
        or "least employees" in question_lower
        or "lowest number of employees" in question_lower
        or "lowest number of active employees" in question_lower
        or "lowest number of inactive employees" in question_lower
        or "lowest number of employees in" in question_lower
    ):

        sql_parts = [
            "SELECT",
            "    department,",
            "    employee_count",
            "FROM (",
            "    SELECT",
            "        d.name AS department,",
            "        COUNT(*) AS employee_count,",
            "        RANK() OVER (ORDER BY COUNT(*) ASC) AS ranking",
            "    FROM reports_employee e",
            "    JOIN reports_department d",
            "        ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=False
        )

        if where_parts:

            sql_parts.append(
                "    WHERE "
                + "\n      AND ".join(
                    where_parts
                )
            )

        sql_parts.extend([
            "    GROUP BY d.id, d.name",
            ") ranked_departments",
            "WHERE ranking = 1",
            "ORDER BY department ASC",
        ])

        return "\n".join(
            sql_parts
        )

    # ========================================================
    # MOST EMPLOYEES BY JOB TITLE
    # ========================================================

    if (
        "job title with the most" in question_lower
        or "job title has the most" in question_lower
        or "most employees by job title" in question_lower
        or "most common job title" in question_lower
    ):

        sql_parts = [
            "SELECT",
            "    job_title,",
            "    employee_count",
            "FROM (",
            "    SELECT",
            "        e.job_title AS job_title,",
            "        COUNT(*) AS employee_count,",
            "        RANK() OVER (ORDER BY COUNT(*) DESC) AS ranking",
            "    FROM reports_employee e",
            "    JOIN reports_department d",
            "        ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=True
        )

        if where_parts:

            sql_parts.append(
                "    WHERE "
                + "\n      AND ".join(
                    where_parts
                )
            )

        sql_parts.extend([
            "    GROUP BY e.job_title",
            ") ranked_job_titles",
            "WHERE ranking = 1",
            "ORDER BY job_title ASC",
        ])

        return "\n".join(
            sql_parts
        )

    # ========================================================
    # FEWEST EMPLOYEES BY JOB TITLE
    # ========================================================

    if (
        "job title with the fewest" in question_lower
        or "job title has the fewest" in question_lower
        or "fewest employees by job title" in question_lower
        or "least employees by job title" in question_lower
        or "least common job title" in question_lower
    ):

        sql_parts = [
            "SELECT",
            "    job_title,",
            "    employee_count",
            "FROM (",
            "    SELECT",
            "        e.job_title AS job_title,",
            "        COUNT(*) AS employee_count,",
            "        RANK() OVER (ORDER BY COUNT(*) ASC) AS ranking",
            "    FROM reports_employee e",
            "    JOIN reports_department d",
            "        ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=True
        )

        if where_parts:

            sql_parts.append(
                "    WHERE "
                + "\n      AND ".join(
                    where_parts
                )
            )

        sql_parts.extend([
            "    GROUP BY e.job_title",
            ") ranked_job_titles",
            "WHERE ranking = 1",
            "ORDER BY job_title ASC",
        ])

        return "\n".join(
            sql_parts
        )

    # ========================================================
    # COUNT QUESTIONS
    # ========================================================

    if is_count_request(question):

        # ====================================================
        # COUNT BY DEPARTMENT
        # ====================================================

        if wants_group_by_department(question):

            sql_parts = [
                "SELECT",
                "    d.name AS department,",
                "    COUNT(*) AS employee_count",
                "FROM reports_employee e",
                "JOIN reports_department d",
                "    ON e.department_id = d.id",
            ]

            where_parts = build_where_parts(
                conditions,
                dataset_id=dataset_id,
                include_department=False
            )

            append_where(
                sql_parts,
                where_parts
            )

            sql_parts.extend([
                "GROUP BY d.id, d.name",
                "ORDER BY employee_count DESC, d.name ASC",
            ])

            return "\n".join(
                sql_parts
            )

        # ====================================================
        # COUNT BY JOB TITLE
        # ====================================================

        if wants_group_by_job_title(question):

            # IMPORTANT FIX:
            # Always JOIN department so a question such as:
            #
            # "How many employees are there for each job title
            #  in the IT department?"
            #
            # can apply:
            #
            # d.name = 'IT'

            sql_parts = [
                "SELECT",
                "    e.job_title,",
                "    COUNT(*) AS employee_count",
                "FROM reports_employee e",
                "JOIN reports_department d",
                "    ON e.department_id = d.id",
            ]

            where_parts = build_where_parts(
                conditions,
                dataset_id=dataset_id,
                include_department=True
            )

            append_where(
                sql_parts,
                where_parts
            )

            sql_parts.extend([
                "GROUP BY e.job_title",
                "ORDER BY employee_count DESC, e.job_title ASC",
            ])

            return "\n".join(
                sql_parts
            )

        # ====================================================
        # TOTAL COUNT
        # ====================================================

        sql_parts = [
            "SELECT",
            "    COUNT(*) AS employee_count",
            "FROM reports_employee e",
            "JOIN reports_department d",
            "    ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=True
        )

        append_where(
            sql_parts,
            where_parts
        )

        return "\n".join(
            sql_parts
        )

    # ========================================================
    # STATUS DETAIL
    # ========================================================

    if status:

        sql_parts = [
            "SELECT",
            "    " + build_employee_select(
                include_status=True
            ),
            "FROM reports_employee e",
            "JOIN reports_department d",
            "    ON e.department_id = d.id",
        ]

        where_parts = build_where_parts(
            conditions,
            dataset_id=dataset_id,
            include_department=True
        )

        append_where(
            sql_parts,
            where_parts
        )

        sql_parts.append(
            "ORDER BY e.employee_id"
        )

        return "\n".join(
            sql_parts
        )

    return None


# ============================================================
# SAVED REPORT MATCHING
# ============================================================

def find_matching_report(
    question,
    user=None
):

    question = clean_question(
        question
    )

    if not question:
        return None

    # Aggregation questions are handled directly.

    if detect_aggregation_request(
        question
    ):
        return None

    if user is not None:

        reports = (
            HRReport.objects
            .filter(is_active=True)
            .filter(
                Q(owner__isnull=True)
                | Q(owner=user)
            )
            .distinct()
        )

    else:

        reports = HRReport.objects.filter(
            is_active=True,
            owner__isnull=True
        )

    question_words = set(
        word.lower()
        for word in re.findall(
            r"[a-zA-Z0-9_]+",
            question
        )
        if len(word) > 2
    )

    best_report = None
    best_score = 0

    for report in reports:

        report_text = " ".join([
            report.name or "",
            report.description or "",
            report.category or "",
        ]).lower()

        score = 0

        for word in question_words:

            if word in report_text:

                score += 1

        if score > best_score:

            best_score = score
            best_report = report

    return best_report


# ============================================================
# AGGREGATION ENFORCEMENT
# ============================================================

def enforce_aggregation(
    sql,
    question
):

    if not sql:
        return sql

    # Fast SQL handles common aggregation and ranking cases.
    # AI-generated aggregation is validated before execution.

    return sql


# ============================================================
# DATASET SECURITY
# ============================================================

def enforce_dataset(
    sql,
    dataset_id
):

    if not sql:

        raise ValueError(
            "SQL query is empty."
        )

    if dataset_id is None:

        raise ValueError(
            "dataset_id is required."
        )

    try:

        dataset_id = int(
            dataset_id
        )

    except (
        TypeError,
        ValueError
    ):

        raise ValueError(
            "dataset_id must be a valid number."
        )

    if dataset_id <= 0:

        raise ValueError(
            "dataset_id must be greater than 0."
        )

    sql = (
        sql
        .strip()
        .rstrip(";")
        .strip()
    )

    dataset_condition = (
        "e.dataset_id = {}".format(
            dataset_id
        )
    )

    # ========================================================
    # Existing dataset filter
    # ========================================================

    existing_dataset_pattern = (
        r"\be\.dataset_id\s*=\s*\d+\b"
    )

    if re.search(
        existing_dataset_pattern,
        sql,
        re.IGNORECASE
    ):

        sql = re.sub(
            existing_dataset_pattern,
            dataset_condition,
            sql,
            flags=re.IGNORECASE
        )

        return sql

    # ========================================================
    # Existing WHERE
    # ========================================================

    if re.search(
        r"\bWHERE\b",
        sql,
        re.IGNORECASE
    ):

        sql = re.sub(
            r"\bWHERE\b",
            "WHERE {}\nAND ".format(
                dataset_condition
            ),
            sql,
            count=1,
            flags=re.IGNORECASE
        )

        return sql

    # ========================================================
    # No WHERE
    # ========================================================

    insertion_match = re.search(
        r"\b("
        r"GROUP\s+BY|"
        r"ORDER\s+BY|"
        r"LIMIT|"
        r"HAVING"
        r")\b",
        sql,
        re.IGNORECASE
    )

    if insertion_match:

        position = insertion_match.start()

        before = sql[
            :position
        ].rstrip()

        after = sql[
            position:
        ]

        return (
            before
            + "\nWHERE "
            + dataset_condition
            + "\n"
            + after
        )

    return (
        sql
        + "\nWHERE "
        + dataset_condition
    )


# ============================================================
# AI SQL GENERATION
# ============================================================

def generate_sql_with_ai(
    question,
    knowledge,
    dataset_id=None
):

    reports_text = []

    for report in knowledge.get(
        "reports",
        []
    ):

        reports_text.append(
            "REPORT NAME: {}\n"
            "DESCRIPTION: {}\n"
            "SQL:\n{}\n".format(
                report.name,
                report.description,
                report.sql_query
            )
        )

    business_rules_text = []

    for rule in knowledge.get(
        "business_rules",
        []
    ):

        business_rules_text.append(
            "BUSINESS RULE: {}\n"
            "{}\n".format(
                rule.name,
                rule.rule_text
            )
        )

    security_rules_text = []

    for rule in knowledge.get(
        "security_rules",
        []
    ):

        security_rules_text.append(
            "SECURITY RULE: {}\n"
            "{}\n".format(
                rule.name,
                rule.rule_text
            )
        )

    prompt = """
You are an HR SQL reporting assistant.

Convert the user's natural-language HR question into
ONE safe MySQL SELECT query.

DATABASE:

Table: reports_employee

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
- dataset_id

Table: reports_department

Columns:
- id
- name
- description

IMPORTANT RULES:

1. Only generate SELECT.
2. Never generate INSERT.
3. Never generate UPDATE.
4. Never generate DELETE.
5. Never generate DROP.
6. Never generate ALTER.
7. Never generate CREATE.
8. Never generate TRUNCATE.
9. Never generate GRANT.
10. Never generate REVOKE.
11. Never generate multiple SQL statements.
12. Use reports_employee as e.
13. Use reports_department as d when needed.
14. Always respect the selected dataset.
15. Do not invent table names.
16. Do not invent columns.

17. For current ACTIVE employees use:

e.status = 'ACTIVE'
AND e.effective_start_date <= CURRENT_DATE
AND (
    e.effective_end_date IS NULL
    OR e.effective_end_date >= CURRENT_DATE
)

18. For historical ACTIVE employees, replace CURRENT_DATE
with the requested historical date.

19. For hire-date questions, filter e.hire_date.
20. Do not apply effective dating to a hire-date-only question
unless the user explicitly asks about effective/historical status.

21. For count questions use COUNT(*).

22. For department-wise questions use:

GROUP BY d.name

23. For job-title-wise questions use:

GROUP BY e.job_title

24. If a job-title-wise question also specifies a department,
you MUST JOIN reports_department and filter using:

d.name = 'Department Name'

25. For "different", "distinct", or "unique" job titles,
use:

COUNT(DISTINCT e.job_title)

26. For "highest", "most", "lowest", or "fewest" questions,
group the requested dimension, calculate COUNT(*), and return
the requested highest or lowest result.

27. If multiple departments/job titles are tied for highest
or lowest, return all tied results.

28. Use RANK() or an equivalent safe SQL technique for ties.

29. Return SQL only.

30. Do not use markdown.

31. Do not explain the SQL.

32. Never query data outside the selected dataset.

33. The selected dataset condition is:

e.dataset_id = {dataset_id}

34. If a WHERE clause exists, include the dataset condition
inside that WHERE clause.

35. If no WHERE clause exists, add one.

36. Always apply all filters explicitly requested by the user.

37. Do not ignore department filters when grouping by job title.

38. Do not ignore job-title filters when grouping by department.

39. Do not replace a requested DISTINCT count with COUNT(*).

SELECTED DATASET ID:
{dataset_id}

USER QUESTION:
{question}

RELEVANT HR REPORTS:
{reports}

BUSINESS RULES:
{business_rules}

SECURITY RULES:
{security_rules}
""".format(
        dataset_id=dataset_id,
        question=question,
        reports="\n\n".join(
            reports_text
        ) or "None",
        business_rules="\n\n".join(
            business_rules_text
        ) or "None",
        security_rules="\n\n".join(
            security_rules_text
        ) or "None"
    )

    sql = ask_ollama(
        prompt
    )

    if not sql:

        raise ValueError(
            "The AI did not generate SQL."
        )

    # ========================================================
    # REMOVE MARKDOWN CODE FENCES
    # ========================================================

    sql = re.sub(
        r"```sql",
        "",
        sql,
        flags=re.IGNORECASE
    )

    sql = re.sub(
        r"```",
        "",
        sql
    )

    sql = sql.strip()

    # ========================================================
    # KEEP ONLY SELECT QUERY
    # ========================================================

    select_match = re.search(
        r"\bSELECT\b",
        sql,
        re.IGNORECASE
    )

    if select_match:

        sql = sql[
            select_match.start():
        ]

    return sql.strip()


# ============================================================
# MAIN HR QUERY ENGINE
# ============================================================

def run_hr_query(
    question,
    dataset_id=None,
    user=None
):

    question = clean_question(
        question
    )

    if not question:

        return {
            "success": False,
            "error": "Question is required."
        }

    if dataset_id is None:

        return {
            "success": False,
            "error": "dataset_id is required."
        }

    try:

        dataset_id = int(
            dataset_id
        )

    except (
        TypeError,
        ValueError
    ):

        return {
            "success": False,
            "error": (
                "dataset_id must be a valid number."
            )
        }

    if dataset_id <= 0:

        return {
            "success": False,
            "error": (
                "dataset_id must be greater than 0."
            )
        }

    # ========================================================
    # 1. FAST SQL
    # ========================================================

    fast_sql = build_fast_hr_sql(
        question,
        dataset_id=dataset_id
    )

    if fast_sql:

        try:

            valid, validation_message = (
                validate_sql(
                    fast_sql
                )
            )

            if not valid:

                return {
                    "success": False,
                    "error": validation_message
                }

            fast_sql = enforce_dataset(
                fast_sql,
                dataset_id
            )

            with connection.cursor() as cursor:

                cursor.execute(
                    fast_sql
                )

                if cursor.description:

                    columns = [
                        column[0]
                        for column in cursor.description
                    ]

                    rows = cursor.fetchall()

                    results = [
                        dict(
                            zip(
                                columns,
                                row
                            )
                        )
                        for row in rows
                    ]

                else:

                    columns = []
                    results = []

            return {
                "success": True,
                "source": "fast_sql",
                "count": len(results),
                "columns": columns,
                "results": results,
                "sql": fast_sql
            }

        except Exception:
            # Continue to saved report / AI.
            pass

    # ========================================================
    # 2. SAVED REPORT
    # ========================================================

    matching_report = find_matching_report(
        question,
        user=user
    )

    if matching_report:

        try:

            sql = (
                matching_report
                .sql_query
                .strip()
            )

            valid, validation_message = (
                validate_sql(
                    sql
                )
            )

            if valid:

                sql = enforce_dataset(
                    sql,
                    dataset_id
                )

                # ------------------------------------------------
                # Fix common MySQL named-parameter syntax.
                # ------------------------------------------------

                department_parameter = False

                if matching_report.name == "Department Employees":

                    if re.search(
                        r":department\b",
                        sql,
                        re.IGNORECASE
                    ):

                        sql = re.sub(
                            r":department\b",
                            "%(department)s",
                            sql,
                            flags=re.IGNORECASE
                        )

                        department_parameter = True

                with connection.cursor() as cursor:

                    if department_parameter:

                        conditions = (
                            extract_requested_conditions(
                                question
                            )
                        )

                        department = conditions.get(
                            "department"
                        )

                        if not department:

                            return {
                                "success": False,
                                "error": (
                                    "Department could not be "
                                    "identified from the question."
                                )
                            }

                        cursor.execute(
                            sql,
                            {
                                "department": department
                            }
                        )

                    else:

                        cursor.execute(
                            sql
                        )

                    if cursor.description:

                        columns = [
                            column[0]
                            for column in cursor.description
                        ]

                        rows = cursor.fetchall()

                        results = [
                            dict(
                                zip(
                                    columns,
                                    row
                                )
                            )
                            for row in rows
                        ]

                    else:

                        columns = []
                        results = []

                return {
                    "success": True,
                    "source": "saved_report",
                    "report": matching_report.name,
                    "count": len(results),
                    "columns": columns,
                    "results": results,
                    "sql": sql
                }

        except Exception:
            # Continue to AI.
            pass

    # ========================================================
    # 3. RAG
    # ========================================================

    try:

        knowledge = retrieve_hr_knowledge(
            question,
            user=user
        )

    except TypeError:

        knowledge = retrieve_hr_knowledge(
            question
        )

    # ========================================================
    # 4. GEMMA 3:4B
    # ========================================================

    try:

        sql = generate_sql_with_ai(
            question,
            knowledge,
            dataset_id=dataset_id
        )

    except Exception as e:

        return {
            "success": False,
            "error": (
                "AI SQL generation failed: {}".format(
                    str(e)
                )
            )
        }

    # ========================================================
    # 5. SQL VALIDATION
    # ========================================================

    valid, validation_message = (
        validate_sql(
            sql
        )
    )

    if not valid:

        return {
            "success": False,
            "error": validation_message,
            "sql": sql
        }

    # ========================================================
    # 6. DATASET SECURITY
    # ========================================================

    try:

        sql = enforce_dataset(
            sql,
            dataset_id
        )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
            "sql": sql
        }

    # ========================================================
    # 7. CLEAN SQL
    # ========================================================

    sql = (
        sql
        .strip()
        .rstrip(";")
        .strip()
    )

    # ========================================================
    # 8. AGGREGATION
    # ========================================================

    sql = enforce_aggregation(
        sql,
        question
    )

    # ========================================================
    # 9. FINAL VALIDATION
    # ========================================================

    valid, validation_message = (
        validate_sql(
            sql
        )
    )

    if not valid:

        return {
            "success": False,
            "error": validation_message,
            "sql": sql
        }

    # ========================================================
    # 10. EXECUTE MYSQL
    # ========================================================

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                sql
            )

            if cursor.description:

                columns = [
                    column[0]
                    for column in cursor.description
                ]

                rows = cursor.fetchall()

                results = [
                    dict(
                        zip(
                            columns,
                            row
                        )
                    )
                    for row in rows
                ]

            else:

                columns = []
                results = []

        return {
            "success": True,
            "source": "ai_generated",
            "count": len(results),
            "columns": columns,
            "results": results,
            "sql": sql
        }

    except Exception as e:

        return {
            "success": False,
            "error": (
                "SQL execution failed: {}".format(
                    str(e)
                )
            ),
            "sql": sql
        }