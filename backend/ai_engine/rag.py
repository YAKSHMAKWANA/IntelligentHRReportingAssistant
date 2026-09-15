from reports.models import HRReport, BusinessRule, SecurityRule

def _score_text(question_words, text):
    """
    Calculate a simple relevance score based on
    meaningful words in the user's question.
    """

    text = (text or "").lower()
    score = 0

    stop_words = {
        "show",
        "me",
        "all",
        "the",
        "a",
        "an",
        "of",
        "to",
        "for",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "who",
        "what",
        "how",
        "many",
        "give",
        "get",
        "please",
        "employees",
        "employee",
        "report",
        "reports",
        "data",
        "records",
    }

    for word in question_words:
        word = word.strip("?,.!:;()[]{}\"'")

        if not word or word in stop_words:
            continue

        if word in text:
            score += 1

    return score


def retrieve_hr_knowledge(question, user=None):
    """
    Retrieve the most relevant HR knowledge for the question.

    Reports:
        - Global/system reports are available to everyone.
        - User-created reports are available only to their owner.

    Business rules and security rules remain globally available.
    """

    question_words = question.lower().split()

    # -------------------------------------------------
    # REPORT ACCESS CONTROL
    # -------------------------------------------------
    #
    # Global reports:
    #     owner = NULL
    #
    # User reports:
    #     owner = current user
    #
    # If a user is provided, return global reports +
    # that user's reports only.
    #
    # If no user is provided, return global reports only.
    # This keeps existing callers safe.
    # -------------------------------------------------

    if user is not None:
        reports = HRReport.objects.filter(
            is_active=True
        ).filter(
            owner__isnull=True
        ) | HRReport.objects.filter(
            is_active=True,
            owner=user
        )

        reports = reports.distinct()

    else:
        reports = HRReport.objects.filter(
            is_active=True,
            owner__isnull=True
        )

    # -------------------------------------------------
    # GLOBAL BUSINESS AND SECURITY RULES
    # -------------------------------------------------

    business_rules = BusinessRule.objects.filter(
        is_active=True
    )

    security_rules = SecurityRule.objects.filter(
        is_active=True
    )

    scored_reports = []
    scored_business_rules = []
    scored_security_rules = []

    # -------------------------------------------------
    # REPORT RETRIEVAL
    # -------------------------------------------------

    for report in reports:

        report_text = " ".join([
            report.name or "",
            report.description or "",
            report.category or "",
            report.sql_query or "",
        ])

        score = _score_text(
            question_words,
            report_text
        )

        if score > 0:
            scored_reports.append(
                (score, report)
            )

    # -------------------------------------------------
    # BUSINESS RULE RETRIEVAL
    # -------------------------------------------------

    for rule in business_rules:

        rule_text = " ".join([
            rule.name or "",
            rule.description or "",
            rule.rule_text or "",
        ])

        score = _score_text(
            question_words,
            rule_text
        )

        if score > 0:
            scored_business_rules.append(
                (score, rule)
            )

    # -------------------------------------------------
    # SECURITY RULE RETRIEVAL
    # -------------------------------------------------

    for rule in security_rules:

        rule_text = " ".join([
            rule.name or "",
            rule.description or "",
            rule.rule_text or "",
        ])

        score = _score_text(
            question_words,
            rule_text
        )

        if score > 0:
            scored_security_rules.append(
                (score, rule)
            )

    # -------------------------------------------------
    # SORT BY RELEVANCE
    # -------------------------------------------------

    scored_reports.sort(
        key=lambda item: item[0],
        reverse=True
    )

    scored_business_rules.sort(
        key=lambda item: item[0],
        reverse=True
    )

    scored_security_rules.sort(
        key=lambda item: item[0],
        reverse=True
    )

    # -------------------------------------------------
    # LIMIT RESULTS
    # -------------------------------------------------

    relevant_reports = [
        item[1]
        for item in scored_reports[:5]
    ]

    relevant_business_rules = [
        item[1]
        for item in scored_business_rules[:5]
    ]

    relevant_security_rules = [
        item[1]
        for item in scored_security_rules[:5]
    ]

    # -------------------------------------------------
    # RETURN RETRIEVED KNOWLEDGE
    # -------------------------------------------------

    return {
        "reports": relevant_reports,
        "business_rules": relevant_business_rules,
        "security_rules": relevant_security_rules,
    }