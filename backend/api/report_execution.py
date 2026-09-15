from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from reports.models import HRReport, Dataset
from ai_engine.report_assistant import enforce_dataset


class RunReportAPIView(APIView):

    # =========================================================
    # Authentication
    # =========================================================

    permission_classes = [IsAuthenticated]

    # =========================================================
    # POST - Run Saved HR Report
    # =========================================================

    def post(self, request, report_id):

        # ---------------------------------------------------------
        # 1. Get selected dataset
        # ---------------------------------------------------------

        dataset_id = request.data.get("dataset_id")

        if not dataset_id:
            return Response(
                {
                    "success": False,
                    "error": "dataset_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dataset_id = int(dataset_id)

        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "error": "dataset_id must be a valid number."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if dataset_id <= 0:
            return Response(
                {
                    "success": False,
                    "error": "dataset_id must be greater than 0."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # 2. IMPORTANT SECURITY CHECK
        #
        # Only allow the logged-in user to run reports against
        # datasets owned by that user.
        # ---------------------------------------------------------

        try:
            dataset = Dataset.objects.get(
                id=dataset_id,
                owner=request.user
            )

        except Dataset.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": (
                        "Selected dataset was not found "
                        "or you do not have permission "
                        "to access it."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ---------------------------------------------------------
        # 3. Get saved HR report
        # ---------------------------------------------------------

        try:
            report = HRReport.objects.get(
                id=report_id,
                is_active=True
            )

        except HRReport.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Report not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ---------------------------------------------------------
        # 4. Get SQL
        # ---------------------------------------------------------

        sql = report.sql_query.strip()

        # ---------------------------------------------------------
        # 5. Only SELECT queries are allowed
        # ---------------------------------------------------------

        if not sql.upper().startswith("SELECT"):
            return Response(
                {
                    "success": False,
                    "error": "Only SELECT queries are allowed."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # 6. Block dangerous SQL commands
        # ---------------------------------------------------------

        forbidden_commands = [
            "DROP ",
            "DELETE ",
            "UPDATE ",
            "INSERT ",
            "ALTER ",
            "TRUNCATE ",
            "CREATE ",
            "GRANT ",
            "REVOKE ",
        ]

        sql_upper = sql.upper()

        for command in forbidden_commands:

            if command in sql_upper:
                return Response(
                    {
                        "success": False,
                        "error": "Unsafe SQL query rejected."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ---------------------------------------------------------
        # 7. Apply selected dataset filter
        # ---------------------------------------------------------

        try:
            sql = enforce_dataset(
                sql,
                dataset_id
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # 8. Clean unnecessary semicolons
        # ---------------------------------------------------------

        sql = sql.strip().rstrip(";").strip()

        # ---------------------------------------------------------
        # 9. Execute report
        # ---------------------------------------------------------

        try:

            with connection.cursor() as cursor:

                # -------------------------------------------------
                # Department Employees requires a department
                # parameter.
                # -------------------------------------------------

                if report.name == "Department Employees":

                    department = request.data.get(
                        "department"
                    )

                    if not department:

                        return Response(
                            {
                                "success": False,
                                "error": (
                                    "Department is required."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    cursor.execute(
                        sql,
                        {
                            "department": department
                        }
                    )

                else:

                    cursor.execute(sql)

                # -------------------------------------------------
                # Get column names
                # -------------------------------------------------

                columns = [
                    column[0]
                    for column in cursor.description
                ]

                # -------------------------------------------------
                # Get rows
                # -------------------------------------------------

                rows = cursor.fetchall()

                # -------------------------------------------------
                # Convert rows to dictionaries
                # -------------------------------------------------

                results = [
                    dict(zip(columns, row))
                    for row in rows
                ]

            # -----------------------------------------------------
            # 10. Return response
            # -----------------------------------------------------

            return Response(
                {
                    "success": True,
                    "report": report.name,

                    "dataset": {
                        "id": dataset.id,
                        "name": dataset.name,
                        "employee_count": (
                            dataset.employee_count
                        ),
                    },

                    "count": len(results),
                    "columns": columns,
                    "results": results,

                    "sql": sql,
                }
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )