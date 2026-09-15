from datetime import date

from django.core.management.base import BaseCommand

from reports.models import (
    Department,
    Employee,
    HRReport,
    BusinessRule,
    SecurityRule,
)


class Command(BaseCommand):
    help = "Create sample HR data"

    def handle(self, *args, **kwargs):

        # Departments
        it, _ = Department.objects.get_or_create(
            name="IT",
            defaults={"description": "Information Technology"},
        )

        hr, _ = Department.objects.get_or_create(
            name="HR",
            defaults={"description": "Human Resources"},
        )

        finance, _ = Department.objects.get_or_create(
            name="Finance",
            defaults={"description": "Finance and Accounting"},
        )

        sales, _ = Department.objects.get_or_create(
            name="Sales",
            defaults={"description": "Sales Department"},
        )

        # Employees
        employees = [
            {
                "employee_id": "EMP001",
                "first_name": "Harsh",
                "last_name": "Makwana",
                "email": "harsh@example.com",
                "department": it,
                "job_title": "Software Developer",
                "hire_date": date(2023, 6, 1),
                "status": "ACTIVE",
                "effective_start_date": date(2023, 6, 1),
            },
            {
                "employee_id": "EMP002",
                "first_name": "Rahul",
                "last_name": "Shah",
                "email": "rahul@example.com",
                "department": it,
                "job_title": "Backend Developer",
                "hire_date": date(2022, 4, 15),
                "status": "ACTIVE",
                "effective_start_date": date(2022, 4, 15),
            },
            {
                "employee_id": "EMP003",
                "first_name": "Priya",
                "last_name": "Patel",
                "email": "priya@example.com",
                "department": hr,
                "job_title": "HR Manager",
                "hire_date": date(2021, 8, 10),
                "status": "ACTIVE",
                "effective_start_date": date(2021, 8, 10),
            },
            {
                "employee_id": "EMP004",
                "first_name": "Amit",
                "last_name": "Joshi",
                "email": "amit@example.com",
                "department": finance,
                "job_title": "Financial Analyst",
                "hire_date": date(2020, 3, 20),
                "status": "ACTIVE",
                "effective_start_date": date(2020, 3, 20),
            },
            {
                "employee_id": "EMP005",
                "first_name": "Neha",
                "last_name": "Mehta",
                "email": "neha@example.com",
                "department": sales,
                "job_title": "Sales Executive",
                "hire_date": date(2024, 1, 5),
                "status": "ON_LEAVE",
                "effective_start_date": date(2024, 1, 5),
            },
            {
                "employee_id": "EMP006",
                "first_name": "Vikas",
                "last_name": "Desai",
                "email": "vikas@example.com",
                "department": it,
                "job_title": "DevOps Engineer",
                "hire_date": date(2025, 2, 12),
                "status": "ACTIVE",
                "effective_start_date": date(2025, 2, 12),
            },
        ]

        for employee_data in employees:
            Employee.objects.update_or_create(
                employee_id=employee_data["employee_id"],
                defaults=employee_data,
            )

        # HR Reports
        HRReport.objects.get_or_create(
            name="Active Employees",
            defaults={
                "description": "List all currently active employees.",
                "sql_query": """
SELECT
    e.employee_id,
    e.first_name,
    e.last_name,
    d.name AS department,
    e.job_title
FROM reports_employee e
JOIN reports_department d
    ON e.department_id = d.id
WHERE e.status = 'ACTIVE'
  AND e.effective_start_date <= CURRENT_DATE
  AND (
      e.effective_end_date IS NULL
      OR e.effective_end_date >= CURRENT_DATE
  );
""",
                "category": "Employee",
            },
        )

        HRReport.objects.get_or_create(
            name="Department Employees",
            defaults={
                "description": "Show employees belonging to a specific department.",
                "sql_query": """
SELECT
    e.employee_id,
    e.first_name,
    e.last_name,
    d.name AS department,
    e.job_title,
    e.status
FROM reports_employee e
JOIN reports_department d
    ON e.department_id = d.id
WHERE d.name = :department;
""",
                "category": "Employee",
            },
        )

        # Business rules
        BusinessRule.objects.get_or_create(
            name="Active Employee Rule",
            defaults={
                "description": "Definition of an active employee.",
                "rule_text": (
                    "An employee is considered active when status is ACTIVE "
                    "and the current date falls within the effective date range."
                ),
            },
        )

        BusinessRule.objects.get_or_create(
            name="Effective Dating Rule",
            defaults={
                "description": "HR records use effective dates.",
                "rule_text": (
                    "When retrieving current HR information, use records whose "
                    "effective_start_date is on or before today and whose "
                    "effective_end_date is either NULL or on or after today."
                ),
            },
        )

        # Security rules
        SecurityRule.objects.get_or_create(
            name="HR Manager Access",
            defaults={
                "description": "HR manager reporting access.",
                "rule_text": (
                    "HR managers can access employee and department reporting data."
                ),
                "allowed_roles": ["HR_MANAGER", "ADMIN"],
            },
        )

        SecurityRule.objects.get_or_create(
            name="Employee Access",
            defaults={
                "description": "Employee reporting access.",
                "rule_text": (
                    "Employees should only be allowed to access information "
                    "permitted by their assigned role."
                ),
                "allowed_roles": ["EMPLOYEE"],
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Sample HR data created successfully!"
            )
        )