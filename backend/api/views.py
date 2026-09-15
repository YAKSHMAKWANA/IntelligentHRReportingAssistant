from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from reports.models import Employee, Dataset
from reports.serializers import EmployeeSerializer


class EmployeeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employees = Employee.objects.select_related("department").filter(
            dataset__owner=request.user
        )

        serializer = EmployeeSerializer(employees, many=True)

        return Response({
            "success": True,
            "count": employees.count(),
            "employees": serializer.data
        })


class DatasetListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        datasets = Dataset.objects.filter(
            owner=request.user
        ).order_by("-uploaded_at")

        data = []

        for dataset in datasets:
            data.append({
                "id": dataset.id,
                "name": dataset.name,
                "file_type": dataset.file_type,
                "employee_count": dataset.employee_count,
                "uploaded_at": dataset.uploaded_at,
            })

        return Response({
            "success": True,
            "count": len(data),
            "datasets": data
        })