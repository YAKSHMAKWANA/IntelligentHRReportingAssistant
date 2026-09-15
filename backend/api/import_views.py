import os
import pandas as pd

from datetime import datetime

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from pypdf import PdfReader

from reports.models import Employee, Department, Dataset


ALLOWED_EXTENSIONS = [
    ".csv",
    ".xlsx",
    ".xls",
    ".pdf",
]


REQUIRED_COLUMNS = [
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "department",
    "job_title",
    "hire_date",
    "status",
]


class ImportHRRecordsAPIView(APIView):

    # =========================================================
    # Authentication
    # =========================================================

    permission_classes = [IsAuthenticated]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    # =========================================================
    # POST - Import HR Dataset
    # =========================================================

    def post(self, request):

        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {
                    "success": False,
                    "error": "Please upload a CSV, Excel, or PDF file.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = uploaded_file.name
        extension = os.path.splitext(filename)[1].lower()

        # =====================================================
        # Validate file type
        # =====================================================

        if extension not in ALLOWED_EXTENSIONS:
            return Response(
                {
                    "success": False,
                    "error": (
                        "Unsupported file type. "
                        "Allowed files: CSV, XLSX, XLS, PDF."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            # =====================================================
            # CSV / EXCEL
            # =====================================================

            if extension == ".csv":

                dataframe = pd.read_csv(uploaded_file)

            elif extension in [".xlsx", ".xls"]:

                dataframe = pd.read_excel(uploaded_file)

            # =====================================================
            # PDF
            # =====================================================

            elif extension == ".pdf":

                dataframe = read_pdf(uploaded_file)

            # =====================================================
            # Normalize column names
            # =====================================================

            dataframe.columns = [
                str(column)
                .strip()
                .lower()
                .replace(" ", "_")
                for column in dataframe.columns
            ]

            # =====================================================
            # Remove completely empty rows
            # =====================================================

            dataframe = dataframe.dropna(how="all")

            # =====================================================
            # Validate required columns
            # =====================================================

            missing_columns = [
                column
                for column in REQUIRED_COLUMNS
                if column not in dataframe.columns
            ]

            if missing_columns:

                return Response(
                    {
                        "success": False,
                        "error": "Missing required columns.",
                        "missing_columns": missing_columns,
                        "available_columns": list(
                            dataframe.columns
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # =====================================================
            # Validate empty file
            # =====================================================

            if dataframe.empty:

                return Response(
                    {
                        "success": False,
                        "error": (
                            "The uploaded file contains "
                            "no employee records."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            imported_count = 0
            skipped_count = 0
            errors = []

            # =====================================================
            # IMPORTANT SECURITY CHANGE
            #
            # The dataset ALWAYS belongs to the authenticated
            # user.
            #
            # There is NO fallback to another user.
            # =====================================================

            user = request.user

            # =====================================================
            # Dataset name
            # =====================================================

            dataset_name = request.data.get(
                "dataset_name",
                ""
            ).strip()

            if not dataset_name:

                dataset_name = os.path.splitext(
                    filename
                )[0]

            # =====================================================
            # Import records inside transaction
            # =====================================================

            with transaction.atomic():

                dataset = Dataset.objects.create(
                    owner=user,
                    name=dataset_name,
                    original_file=uploaded_file,
                    file_type=extension.replace(
                        ".",
                        ""
                    ).upper(),
                    employee_count=0,
                )

                # =================================================
                # Process every employee row
                # =================================================

                for index, row in dataframe.iterrows():

                    row_number = index + 2

                    try:

                        # -----------------------------------------
                        # Basic values
                        # -----------------------------------------

                        employee_id = self.clean_value(
                            row.get("employee_id")
                        )

                        first_name = self.clean_value(
                            row.get("first_name")
                        )

                        last_name = self.clean_value(
                            row.get("last_name")
                        )

                        email = self.clean_value(
                            row.get("email")
                        )

                        department_name = self.clean_value(
                            row.get("department")
                        )

                        job_title = self.clean_value(
                            row.get("job_title")
                        )

                        # -----------------------------------------
                        # Dates
                        # -----------------------------------------

                        hire_date = self.parse_date(
                            row.get("hire_date")
                        )

                        effective_start_date = self.parse_date(
                            row.get(
                                "effective_start_date"
                            )
                        )

                        effective_end_date = self.parse_date(
                            row.get(
                                "effective_end_date"
                            )
                        )

                        # -----------------------------------------
                        # Status
                        # -----------------------------------------

                        status_value = self.clean_value(
                            row.get("status")
                        ).upper()

                        # -----------------------------------------
                        # Required validation
                        # -----------------------------------------

                        if not employee_id:

                            raise ValueError(
                                "employee_id is required"
                            )

                        if not first_name:

                            raise ValueError(
                                "first_name is required"
                            )

                        if not last_name:

                            raise ValueError(
                                "last_name is required"
                            )

                        if not email:

                            raise ValueError(
                                "email is required"
                            )

                        if not department_name:

                            raise ValueError(
                                "department is required"
                            )

                        if not job_title:

                            raise ValueError(
                                "job_title is required"
                            )

                        if not hire_date:

                            raise ValueError(
                                "valid hire_date is required"
                            )

                        # -----------------------------------------
                        # Validate status
                        # -----------------------------------------

                        allowed_statuses = [
                            "ACTIVE",
                            "INACTIVE",
                            "ON_LEAVE",
                        ]

                        if status_value not in allowed_statuses:

                            raise ValueError(
                                "status must be ACTIVE, "
                                "INACTIVE, or ON_LEAVE"
                            )

                        # -----------------------------------------
                        # Effective start date
                        # -----------------------------------------

                        if not effective_start_date:

                            effective_start_date = hire_date

                        # -----------------------------------------
                        # Department
                        # -----------------------------------------

                        department, _ = (
                            Department.objects.get_or_create(
                                name=department_name
                            )
                        )

                        # -----------------------------------------
                        # Duplicate employee ID
                        #
                        # Only checked inside this dataset.
                        # -----------------------------------------

                        if Employee.objects.filter(
                            dataset=dataset,
                            employee_id=employee_id
                        ).exists():

                            raise ValueError(
                                "Duplicate employee_id "
                                "in this dataset"
                            )

                        # -----------------------------------------
                        # Duplicate email
                        #
                        # Only checked inside this dataset.
                        # -----------------------------------------

                        if Employee.objects.filter(
                            dataset=dataset,
                            email=email
                        ).exists():

                            raise ValueError(
                                "Duplicate email "
                                "in this dataset"
                            )

                        # -----------------------------------------
                        # Create employee
                        #
                        # We NEVER modify employees from
                        # another dataset.
                        # -----------------------------------------

                        Employee.objects.create(
                            dataset=dataset,
                            employee_id=employee_id,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            department=department,
                            job_title=job_title,
                            hire_date=hire_date,
                            status=status_value,
                            effective_start_date=effective_start_date,
                            effective_end_date=effective_end_date,
                        )

                        imported_count += 1

                    except Exception as row_error:

                        skipped_count += 1

                        errors.append(
                            {
                                "row": row_number,
                                "error": str(row_error),
                            }
                        )

                # =================================================
                # Update dataset employee count
                # =================================================

                dataset.employee_count = imported_count

                dataset.save(
                    update_fields=[
                        "employee_count"
                    ]
                )

            # =====================================================
            # Success response
            # =====================================================

            return Response(
                {
                    "success": True,
                    "message": (
                        "HR dataset imported successfully."
                    ),
                    "dataset": {
                        "id": dataset.id,
                        "name": dataset.name,
                        "file_name": filename,
                        "file_type": dataset.file_type,
                        "employee_count": (
                            dataset.employee_count
                        ),
                        "owner": user.username,
                    },
                    "total_rows": len(dataframe),
                    "imported": imported_count,
                    "skipped": skipped_count,
                    "errors": errors[:20],
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # =============================================================
    # Helper: Clean values
    # =============================================================

    def clean_value(self, value):

        if value is None:

            return ""

        try:

            if pd.isna(value):

                return ""

        except Exception:

            pass

        return str(value).strip()

    # =============================================================
    # Helper: Parse dates
    # =============================================================

    def parse_date(self, value):

        if value is None:

            return None

        try:

            if pd.isna(value):

                return None

        except Exception:

            pass

        # ---------------------------------------------------------
        # Python datetime
        # ---------------------------------------------------------

        if isinstance(value, datetime):

            return value.date()

        # ---------------------------------------------------------
        # Pandas Timestamp / date-like object
        # ---------------------------------------------------------

        if hasattr(value, "date"):

            try:

                return value.date()

            except Exception:

                pass

        value = str(value).strip()

        if not value:

            return None

        # ---------------------------------------------------------
        # Supported date formats
        # ---------------------------------------------------------

        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
        ]

        for date_format in formats:

            try:

                return datetime.strptime(
                    value,
                    date_format
                ).date()

            except ValueError:

                continue

        # ---------------------------------------------------------
        # Pandas fallback
        # ---------------------------------------------------------

        try:

            return pd.to_datetime(value).date()

        except Exception:

            raise ValueError(
                "Invalid date format: " + value
            )


# =================================================================
# PDF READER
#
# IMPORTANT:
# This function is OUTSIDE ImportHRRecordsAPIView.
# =================================================================

def read_pdf(uploaded_file):

    reader = PdfReader(uploaded_file)

    lines = []

    # =============================================================
    # Extract text from every page
    # =============================================================

    for page in reader.pages:

        text = page.extract_text()

        if text:

            page_lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            lines.extend(page_lines)

    # =============================================================
    # Remove PDF title and column headers
    # =============================================================

    headers = {
        "employee_id",
        "first_name",
        "last_name",
        "email",
        "department",
        "job_title",
        "hire_date",
        "status",
        "effective_start_date",
        "effective_end_date",
    }

    lines = [
        line
        for line in lines
        if line not in headers
        and not line.startswith(
            "HR Employee Records"
        )
        and not line.startswith(
            "Demo dataset"
        )
    ]

    # =============================================================
    # Build employee records
    # =============================================================

    records = []

    i = 0

    while i < len(lines):

        # ---------------------------------------------------------
        # Every employee starts with EMP
        # ---------------------------------------------------------

        if not lines[i].startswith("EMP"):

            i += 1

            continue

        employee_id = lines[i]

        i += 1

        # ---------------------------------------------------------
        # Need at least:
        #
        # first_name
        # last_name
        # email
        # department
        # job_title
        # hire_date
        # status
        # effective_start_date
        # ---------------------------------------------------------

        if i + 7 >= len(lines):

            break

        first_name = lines[i]

        i += 1

        last_name = lines[i]

        i += 1

        email = lines[i]

        i += 1

        department = lines[i]

        i += 1

        job_title = lines[i]

        i += 1

        hire_date = lines[i]

        i += 1

        status = lines[i]

        i += 1

        effective_start_date = lines[i]

        i += 1

        # =========================================================
        # Effective end date exists only for INACTIVE employees
        # =========================================================

        effective_end_date = None

        if status == "INACTIVE":

            if i < len(lines):

                effective_end_date = lines[i]

                i += 1

        # =========================================================
        # Add record
        # =========================================================

        records.append(
            {
                "employee_id": employee_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "department": department,
                "job_title": job_title,
                "hire_date": hire_date,
                "status": status,
                "effective_start_date": (
                    effective_start_date
                ),
                "effective_end_date": (
                    effective_end_date
                ),
            }
        )

    # =============================================================
    # Make sure records were found
    # =============================================================

    if not records:

        raise ValueError(
            "No employee records could be extracted "
            "from the PDF."
        )

    return pd.DataFrame(records)