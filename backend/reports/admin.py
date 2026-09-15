from django.contrib import admin

from .models import (
    Department,
    Dataset,
    Employee,
    HRReport,
    BusinessRule,
    SecurityRule,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
    )
    search_fields = (
        "name",
    )


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
        "file_type",
        "employee_count",
        "uploaded_at",
    )
    search_fields = (
        "name",
        "owner__username",
    )
    list_filter = (
        "file_type",
        "uploaded_at",
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee_id",
        "first_name",
        "last_name",
        "email",
        "department",
        "job_title",
        "status",
        "dataset",
    )
    search_fields = (
        "employee_id",
        "first_name",
        "last_name",
        "email",
        "job_title",
    )
    list_filter = (
        "status",
        "department",
        "dataset",
    )


@admin.register(HRReport)
class HRReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
        "category",
        "is_active",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "name",
        "description",
        "category",
        "owner__username",
    )
    list_filter = (
        "category",
        "is_active",
        "created_at",
    )


@admin.register(BusinessRule)
class BusinessRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "rule_text",
    )
    list_filter = (
        "is_active",
        "created_at",
    )


@admin.register(SecurityRule)
class SecurityRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "is_active",
    )
    search_fields = (
        "name",
        "description",
        "rule_text",
    )
    list_filter = (
        "is_active",
    )