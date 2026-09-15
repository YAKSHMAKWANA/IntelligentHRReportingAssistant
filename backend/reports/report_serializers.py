from rest_framework import serializers
from .models import HRReport


class HRReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRReport
        fields = [
            "id",
            "name",
            "description",
            "category",
            "is_active",
            "created_at",
            "updated_at",
        ]