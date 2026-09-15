from django.urls import path

from .views import EmployeeListAPIView, DatasetListAPIView
from .report_views import HRReportListAPIView, HRReportCreateAPIView
from .report_execution import RunReportAPIView
from .assistant_views import HRAssistantAPIView
from .import_views import ImportHRRecordsAPIView

urlpatterns = [
    path(
        "employees/",
        EmployeeListAPIView.as_view(),
        name="employees"
    ),

   path("reports/", HRReportListAPIView.as_view(), name="reports"),

    path(
        "reports/create/",
        HRReportCreateAPIView.as_view(),
        name="create-report"
    ),

    path(
        "reports/<int:report_id>/run/",
        RunReportAPIView.as_view(),
        name="run-report"
    ),

    path(
        "assistant/",
        HRAssistantAPIView.as_view(),
        name="hr-assistant"
    ),

    path(
        "import/",
        ImportHRRecordsAPIView.as_view(),
        name="import-hr-records"
    ),

    path("datasets/", DatasetListAPIView.as_view(), name="datasets"),
]