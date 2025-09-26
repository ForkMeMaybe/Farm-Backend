from rest_framework import serializers
from .models import (
    Livestock,
    HealthRecord,
    AMURecord,
    FeedRecord,
    YieldRecord,
    Farm,
    Labourer,
    Drug, # Import Drug model
    Feed,
)


class FarmSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Farm
        fields = "__all__"


class LabourerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    farm_name = serializers.CharField(source="farm.name", read_only=True)

    class Meta:
        model = Labourer
        fields = (
            "id",
            "user",
            "farm",
            "status",
            "user_name",
            "user_email",
            "farm_name",
        )
        read_only_fields = ("user", "farm", "status")


class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = "__all__"


class FeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feed
        fields = "__all__"


class LivestockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livestock
        fields = [
            "id",
            "gender",
            "health_status",
            "tag_id",
            "species",
            "breed",
            "date_of_birth",
            "current_weight_kg", # New field
        ]


class AMURecordSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.name', read_only=True) # Display drug name
    class Meta:
        model = AMURecord
        fields = ["id", "health_record", "drug", "drug_name", "dosage", "withdrawal_period"]


class HealthRecordSerializer(serializers.ModelSerializer):
    amu_records = AMURecordSerializer(many=True, read_only=True)

    class Meta:
        model = HealthRecord
        fields = ["id", "livestock", "event_type", "event_date", "notes", "diagnosis", "treatment_outcome", "amu_records"]


class FeedRecordSerializer(serializers.ModelSerializer):
    feed_name = serializers.CharField(source="feed.name", read_only=True)
    class Meta:
        model = FeedRecord
        fields = ["id", "livestock", "feed_type", "feed", "feed_name", "quantity_kg", "price_per_kg", "date"]


class YieldRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = YieldRecord
        fields = ["id", "livestock", "yield_type", "quantity", "unit", "date"]