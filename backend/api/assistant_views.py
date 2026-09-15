from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from reports.models import Dataset
from ai_engine.report_assistant import run_hr_query


class HRAssistantAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        # -------------------------------------------------
        # Get question
        # -------------------------------------------------

        question = request.data.get(
            "question",
            ""
        ).strip()

        # -------------------------------------------------
        # Get dataset ID
        # -------------------------------------------------

        dataset_id = request.data.get(
            "dataset_id"
        )

        # -------------------------------------------------
        # Validate question
        # -------------------------------------------------

        if not question:

            return Response(
                {
                    "success": False,
                    "error": "Question is required."
                },
                status=400
            )

        # -------------------------------------------------
        # Validate dataset ID
        # -------------------------------------------------

        if not dataset_id:

            return Response(
                {
                    "success": False,
                    "error": "dataset_id is required."
                },
                status=400
            )

        try:

            dataset_id = int(dataset_id)

        except (TypeError, ValueError):

            return Response(
                {
                    "success": False,
                    "error": "dataset_id must be a valid number."
                },
                status=400
            )

        if dataset_id <= 0:

            return Response(
                {
                    "success": False,
                    "error": "dataset_id must be greater than 0."
                },
                status=400
            )

        # -------------------------------------------------
        # SECURITY:
        # Make sure the selected dataset belongs
        # to the currently logged-in user.
        # -------------------------------------------------

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
                status=404
            )

        # -------------------------------------------------
        # RUN HR ASSISTANT
        #
        # IMPORTANT:
        # Pass request.user so RAG and saved-report
        # matching are user-aware.
        # -------------------------------------------------

        result = run_hr_query(
            question,
            dataset_id=dataset.id,
            user=request.user
        )

        # -------------------------------------------------
        # Handle query error
        # -------------------------------------------------

        if not result["success"]:

            return Response(
                result,
                status=400
            )

        # -------------------------------------------------
        # Add dataset information to response
        # -------------------------------------------------

        result["dataset"] = {
            "id": dataset.id,
            "name": dataset.name,
            "employee_count": dataset.employee_count,
        }

        # -------------------------------------------------
        # Return final response
        # -------------------------------------------------

        return Response(result)