from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .views_insights import AMUInsightsViewSet
from .views_insights import FeedInsightsViewSet, YieldInsightsViewSet
import os
from .models import (
    Farm,
    Labourer,
    Livestock,
    HealthRecord,
    AMURecord,
    FeedRecord,
    YieldRecord,
    Drug,
    Feed,
)
from .permissions import IsFarmOwner, IsFarmMember
from .serializers import (
    FarmSerializer,
    LabourerSerializer,
    LivestockSerializer,
    HealthRecordSerializer,
    AMURecordSerializer,
    FeedRecordSerializer,
    YieldRecordSerializer,
    DrugSerializer,
    FeedSerializer,
)

import requests


class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Farm.objects.all()
        return Farm.objects.none()

    def get_permissions(self):
        if self.action == "list":
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsFarmOwner]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LabourerViewSet(viewsets.ModelViewSet):
    serializer_class = LabourerSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "owned_farm"):
            return Labourer.objects.filter(farm=user.owned_farm)
        elif hasattr(user, "labourer_profile"):
            return Labourer.objects.filter(user=user)
        return Labourer.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsFarmMember()]

    def perform_create(self, serializer):
        if hasattr(self.request.user, "labourer_profile"):
            raise PermissionDenied("You already have a labourer profile.")
        serializer.save(user=self.request.user, status="pending", farm=None)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join_farm(self, request, pk=None):
        farm = get_object_or_404(Farm, pk=pk)

        try:
            labourer = Labourer.objects.get(user=request.user)
        except Labourer.DoesNotExist:
            return Response(
                {"detail": "Labourer profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if labourer.farm is not None:
            if labourer.farm == farm and labourer.status == "pending":
                return Response(
                    {"detail": "You have already sent a request to join this farm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif labourer.farm == farm and labourer.status == "approved":
                return Response(
                    {"detail": "You are already an approved member of this farm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif labourer.farm != farm and labourer.status == "pending":
                return Response(
                    {
                        "detail": "You have a pending request for another farm. Please wait for approval or rejection."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif labourer.farm != farm and labourer.status == "approved":
                return Response(
                    {"detail": "You are already an approved member of another farm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        labourer.farm = farm
        labourer.status = "pending"
        labourer.save()

        send_mail(
            "New Labourer Request",
            f'{request.user.username} wants to join your farm, "{farm.name}". Go to your dashboard to approve or reject.',
            "noreply@farm.com",
            [farm.owner.email],
            fail_silently=False,
        )

        return Response(
            {"detail": "Request to join farm sent."}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsFarmOwner],
        url_path="approve",
    )
    def approve_labourer(self, request, pk=None):
        labourer = self.get_object()
        if labourer.farm.owner != request.user:
            return Response(
                {"detail": "You are not the owner of this farm."},
                status=status.HTTP_403_FORBIDDEN,
            )

        labourer.status = "approved"
        labourer.save()

        send_mail(
            "Farm Join Request Approved",
            f'Your request to join the farm "{labourer.farm.name}" has been approved.',
            "noreply@farm.com",
            [labourer.user.email],
            fail_silently=False,
        )

        return Response({"detail": "Labourer approved."}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsFarmOwner],
        url_path="reject",
    )
    def reject_labourer(self, request, pk=None):
        labourer = self.get_object()
        if labourer.farm.owner != request.user:
            return Response(
                {"detail": "You are not the owner of this farm."},
                status=status.HTTP_403_FORBIDDEN,
            )

        labourer.status = "rejected"
        labourer.save()
        return Response({"detail": "Labourer rejected."}, status=status.HTTP_200_OK)


class DrugViewSet(viewsets.ModelViewSet):
    serializer_class = DrugSerializer
    permission_classes = [IsAuthenticated, IsFarmOwner]  # Only owners can manage drugs

    def get_queryset(self):
        return Drug.objects.all()


class FeedViewSet(viewsets.ModelViewSet):
    serializer_class = FeedSerializer
    permission_classes = [IsAuthenticated, IsFarmOwner]

    def get_queryset(self):
        return Feed.objects.all()


class AMUInsightsViewSet(viewsets.ViewSet):
    permission_classes = [
        IsAuthenticated,
        IsFarmOwner,
    ]

    @action(detail=False, methods=["GET"], url_path="chart-data")
    def chart_data(self, request):
        livestock_id = request.query_params.get("livestock_id")
        if not livestock_id:
            return Response(
                {"error": "livestock_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            livestock = Livestock.objects.get(pk=livestock_id, farm__owner=request.user)
        except Livestock.DoesNotExist:
            return Response(
                {"detail": "Livestock not found or you don't own it."},
                status=status.HTTP_404_NOT_FOUND,
            )

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        amu_records = AMURecord.objects.filter(
            health_record__livestock_id=livestock_id,
            health_record__event_date__gte=start_date,
            health_record__event_date__lte=end_date,
        )

        monthly_usage = (
            amu_records.annotate(month=TruncMonth("health_record__event_date"))
            .values("month", "drug__name")
            .annotate(count=Count("id"))
            .order_by("month", "drug__name")
        )

        chart_data = {"labels": [], "datasets": []}

        drugs = Drug.objects.filter(
            id__in=amu_records.values_list("drug_id", flat=True)
        ).distinct()
        drug_datasets = {drug.name: [] for drug in drugs}

        months = []
        current = start_date
        while current <= end_date:
            month_str = current.strftime("%Y-%m")
            months.append(month_str)
            for drug_data in drug_datasets.values():
                drug_data.append(0)
            current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)

        for record in monthly_usage:
            month_str = record["month"].strftime("%Y-%m")
            if month_str in months:
                month_index = months.index(month_str)
                drug_name = record["drug__name"]
                if drug_name in drug_datasets:
                    drug_datasets[drug_name][month_index] = record["count"]

        formatted_labels = [
            datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months
        ]
        chart_data["labels"] = formatted_labels

        colors = [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
            "#FF9F40",
            "#FF6384",
            "#C9CBCF",
            "#4BC0C0",
            "#FF9F40",
        ]

        for i, (drug_name, counts) in enumerate(drug_datasets.items()):
            dataset = {
                "label": drug_name,
                "data": counts,
                "backgroundColor": colors[i % len(colors)],
                "borderColor": colors[i % len(colors)],
                "borderWidth": 1,
                "fill": False,
            }
            chart_data["datasets"].append(dataset)

        return Response(
            {
                "chart_data": chart_data,
                "summary": {
                    "total_treatments": amu_records.count(),
                    "unique_drugs": len(drugs),
                    "time_period": f"{formatted_labels[0]} to {formatted_labels[-1]}",
                },
            }
        )

    @action(detail=False, methods=["post"], url_path="generate")
    def generate_insights(self, request):
        livestock_id = request.data.get("livestock_id")

        if not livestock_id:
            return Response(
                {"detail": "livestock_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            livestock = Livestock.objects.get(pk=livestock_id, farm__owner=request.user)
        except Livestock.DoesNotExist:
            return Response(
                {"detail": "Livestock not found or you don't own it."},
                status=status.HTTP_404_NOT_FOUND,
            )

        amu_records = AMURecord.objects.filter(
            health_record__livestock=livestock
        ).order_by("-health_record__event_date")[:5]
        health_records = HealthRecord.objects.filter(livestock=livestock).order_by(
            "-event_date"
        )[:5]

        livestock_data = LivestockSerializer(livestock).data
        amu_data = AMURecordSerializer(amu_records, many=True).data
        health_data = HealthRecordSerializer(health_records, many=True).data

        prompt = f"""
        Analyze the following data for a livestock animal and provide insights on AMU (Antimicrobial Usage).
        Determine if the current drug dosages are correct based on recommended ranges and animal weight.
        If not correct, suggest adjustments (e.g., bring the dosage up or down by X quantity).
        Also, provide any additional relevant insights about the animal's health and drug usage.

        Livestock Details:
        - Species: {livestock_data.get("species")}
        - Breed: {livestock_data.get("breed")}
        - Gender: {livestock_data.get("gender")}
        - Current Weight (kg): {livestock_data.get("current_weight_kg")}
        - Health Status: {livestock_data.get("health_status")}

        Recent Health Records:
        {health_data}

        Recent AMU Records:
        {amu_data}

        Recommended Drug Information (if available in AMU records):
        """

        for amu_record in amu_records:
            if amu_record.drug:
                drug_info = DrugSerializer(amu_record.drug).data
                prompt += f"""
                - Drug Name: {drug_info.get("name")}
                - Active Ingredient: {drug_info.get("active_ingredient")}
                - Species Target: {drug_info.get("species_target")}
                - Recommended Dosage Min: {drug_info.get("recommended_dosage_min")} {drug_info.get("unit")}
                - Recommended Dosage Max: {drug_info.get("recommended_dosage_max")} {drug_info.get("unit")}
                """

        try:
            # Configure Perplexity API
            api_key = os.getenv("PERPLEXITY_API_KEY")
            url = "https://api.perplexity.ai/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert veterinary assistant specializing in livestock health and antimicrobial usage (AMU) analysis. Provide detailed, professional insights about animal health, drug dosages, and treatment recommendations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1500,
                "temperature": 0.7,
            }

            # Retry logic for better reliability
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        url, json=data, headers=headers, timeout=None
                    )

                    if response.status_code == 200:
                        result = response.json()
                        insights = result["choices"][0]["message"]["content"]
                        break
                    else:
                        if attempt == max_retries - 1:  # Last attempt
                            insights = f"Error generating insights: {response.status_code} - {response.text}"
                        else:
                            continue  # Retry

                except requests.exceptions.Timeout:
                    if attempt == max_retries - 1:  # Last attempt
                        insights = "Error generating insights: Request timeout after multiple attempts. Please try again."
                    else:
                        continue  # Retry

                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:  # Last attempt
                        insights = f"Error generating insights: {str(e)}"
                    else:
                        continue  # Retry

        except Exception as e:
            insights = f"Error generating insights: {str(e)}"

        return Response({"insights": insights}, status=status.HTTP_200_OK)


class LivestockViewSet(viewsets.ModelViewSet):
    serializer_class = LivestockSerializer
    permission_classes = [IsAuthenticated, IsFarmMember]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "owned_farm"):
            return Livestock.objects.filter(farm=user.owned_farm)
        elif hasattr(user, "labourer_profile") and user.labourer_profile.farm:
            return Livestock.objects.filter(farm=user.labourer_profile.farm)
        return Livestock.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "owned_farm"):
            raise PermissionDenied("Only farm owners can add livestock.")
        serializer.save(farm=user.owned_farm)


class HealthRecordViewSet(viewsets.ModelViewSet):
    serializer_class = HealthRecordSerializer
    permission_classes = [IsAuthenticated, IsFarmMember]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "owned_farm"):
            return HealthRecord.objects.filter(livestock__farm=user.owned_farm)
        elif hasattr(user, "labourer_profile") and user.labourer_profile.farm:
            return HealthRecord.objects.filter(
                livestock__farm=user.labourer_profile.farm
            )
        return HealthRecord.objects.none()


class AMURecordViewSet(viewsets.ModelViewSet):
    serializer_class = AMURecordSerializer
    permission_classes = [IsAuthenticated, IsFarmMember]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "owned_farm"):
            return AMURecord.objects.filter(
                health_record__livestock__farm=user.owned_farm
            )
        elif hasattr(user, "labourer_profile") and user.labourer_profile.farm:
            return AMURecord.objects.filter(
                health_record__livestock__farm=user.labourer_profile.farm
            )
        return AMURecord.objects.none()


class FeedRecordViewSet(viewsets.ModelViewSet):
    serializer_class = FeedRecordSerializer
    permission_classes = [IsAuthenticated, IsFarmMember]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "owned_farm"):
            return FeedRecord.objects.filter(livestock__farm=user.owned_farm)
        elif hasattr(user, "labourer_profile") and user.labourer_profile.farm:
            return FeedRecord.objects.filter(livestock__farm=user.labourer_profile.farm)
        return FeedRecord.objects.none()


class YieldRecordViewSet(viewsets.ModelViewSet):
    serializer_class = YieldRecordSerializer
    permission_classes = [IsAuthenticated, IsFarmMember]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "owned_farm"):
            return YieldRecord.objects.filter(livestock__farm=user.owned_farm)
        elif hasattr(user, "labourer_profile") and user.labourer_profile.farm:
            return YieldRecord.objects.filter(
                livestock__farm=user.labourer_profile.farm
            )
        return YieldRecord.objects.none()
