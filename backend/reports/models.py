from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Dataset(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hr_datasets"
    )
    name = models.CharField(max_length=200)
    original_file = models.FileField(
        upload_to="hr_datasets/",
        blank=True,
        null=True
    )
    file_type = models.CharField(max_length=20, blank=True)
    employee_count = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("ON_LEAVE", "On Leave"),
    ]

    employee_id = models.CharField(max_length=20)

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="employees",
        null=True,
        blank=True
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees"
    )

    job_title = models.CharField(max_length=100)
    hire_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    effective_start_date = models.DateField()
    effective_end_date = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "employee_id"],
                name="unique_employee_per_dataset"
            )
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"


class HRReport(models.Model):
    # NULL owner means this is a global/system report.
    # A specific user means this is that user's custom report.
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hr_reports",
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=200,
        unique=True
    )

    description = models.TextField()

    sql_query = models.TextField()

    category = models.CharField(
        max_length=100,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name


class BusinessRule(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    rule_text = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SecurityRule(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    rule_text = models.TextField()
    allowed_roles = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name