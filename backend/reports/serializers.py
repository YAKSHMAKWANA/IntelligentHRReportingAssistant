from rest_framework import serializers

from .models import Employee, Dataset


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "first_name",
            "last_name",
            "email",
            "department",
            "department_name",
            "job_title",
            "hire_date",
            "status",
            "effective_start_date",
            "effective_end_date",
        ]


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "file_type",
            "employee_count",
            "uploaded_at",
        ]