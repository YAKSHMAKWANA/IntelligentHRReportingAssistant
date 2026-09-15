from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from reports.models import HRReport
from reports.report_serializers import HRReportSerializer


class HRReportListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Show:
        # 1. Global/system reports (owner=None)
        # 2. Reports created by the currently logged-in user
        reports = HRReport.objects.filter(
            is_active=True
        ).filter(
            owner__isnull=True
        ) | HRReport.objects.filter(
            is_active=True,
            owner=request.user
        )

        reports = reports.distinct().order_by("name")

        serializer = HRReportSerializer(
            reports,
            many=True
        )

        return Response({
            "success": True,
            "count": reports.count(),
            "reports": serializer.data
        })


class HRReportCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get("name", "").strip()
        description = request.data.get("description", "").strip()
        sql_query = request.data.get("sql_query", "").strip()
        category = request.data.get("category", "").strip()

        # -----------------------------
        # Validate report name
        # -----------------------------
        if not name:
            return Response(
                {
                    "success": False,
                    "error": "Report name is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # Validate description
        # -----------------------------
        if not description:
            return Response(
                {
                    "success": False,
                    "error": "Report description is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # Validate SQL
        # -----------------------------
        if not sql_query:
            return Response(
                {
                    "success": False,
                    "error": "SQL query is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only SELECT queries are allowed
        if not sql_query.upper().startswith("SELECT"):
            return Response(
                {
                    "success": False,
                    "error": "Only SELECT queries are allowed."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # Block dangerous SQL commands
        # -----------------------------
        forbidden_commands = [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "TRUNCATE",
            "CREATE",
            "GRANT",
            "REVOKE",
        ]

        sql_upper = sql_query.upper()

        for command in forbidden_commands:
            if command in sql_upper:
                return Response(
                    {
                        "success": False,
                        "error": "Unsafe SQL query rejected."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # -----------------------------
        # Check duplicate report name
        # -----------------------------
        if HRReport.objects.filter(name=name).exists():
            return Response(
                {
                    "success": False,
                    "error": "A report with this name already exists."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # Create report
        # -----------------------------
        report = HRReport.objects.create(
            owner=request.user,
            name=name,
            description=description,
            sql_query=sql_query,
            category=category,
            is_active=True
        )

        serializer = HRReportSerializer(report)

        return Response(
            {
                "success": True,
                "message": "HR report added successfully.",
                "report": serializer.data
            },
            status=status.HTTP_201_CREATED
        )