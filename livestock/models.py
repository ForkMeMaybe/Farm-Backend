from django.conf import settings
from django.db import models


class Farm(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="owned_farm", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.username})"


class Labourer(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="labourer_profile",
        on_delete=models.CASCADE,
    )
    farm = models.ForeignKey(
        Farm, related_name="labourers", on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        farm_name = self.farm.name if self.farm else "No Farm"
        return f"{self.user.username} @ {farm_name} ({self.status})"


class Livestock(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE)
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    HEALTH_STATUS_CHOICES = [
        ("healthy", "Healthy"),
        ("sick", "Sick"),
        ("recovering", "Recovering"),
    ]

    tag_id = models.CharField(max_length=100, unique=True)
    species = models.CharField(max_length=100)
    breed = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    health_status = models.CharField(
        max_length=20, choices=HEALTH_STATUS_CHOICES, default="healthy"
    )
    current_weight_kg = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.species} - {self.tag_id}"


class Drug(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active_ingredient = models.CharField(max_length=100, blank=True, null=True)
    species_target = models.CharField(max_length=100, blank=True, null=True)
    recommended_dosage_min = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    recommended_dosage_max = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Feed(models.Model):
    name = models.CharField(max_length=100, unique=True)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class HealthRecord(models.Model):
    EVENT_CHOICES = [
        ("vaccination", "Vaccination"),
        ("sickness", "Sickness"),
        ("check-up", "Check-up"),
        ("treatment", "Treatment"),
    ]
    livestock = models.ForeignKey(
        Livestock, related_name="health_records", on_delete=models.CASCADE
    )
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    event_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    diagnosis = models.CharField(max_length=255, blank=True, null=True)  
    treatment_outcome = models.CharField(
        max_length=20, blank=True, null=True
    )

    def __str__(self):
        return f"{self.event_type} for {self.livestock.tag_id} on {self.event_date}"


class AMURecord(models.Model):
    health_record = models.ForeignKey(
        HealthRecord, related_name="amu_records", on_delete=models.CASCADE
    )
    drug = models.ForeignKey(
        Drug,
        related_name="amu_records",
        on_delete=models.CASCADE,
        null=True,
        blank=True,  
    )
    dosage = models.CharField(max_length=50)
    withdrawal_period = models.PositiveIntegerField(
        help_text="Days until livestock product is safe for consumption"
    )

    def __str__(self):
        return f"Drug: {self.drug.name if self.drug else 'N/A'} for Health Record ID: {self.health_record.id}"


class FeedRecord(models.Model):
    livestock = models.ForeignKey(
        Livestock, related_name="feed_records", on_delete=models.CASCADE
    )
    feed_type = models.CharField(max_length=100)
    feed = models.ForeignKey(
        Feed,
        related_name="feed_records",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    quantity_kg = models.DecimalField(max_digits=7, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    date = models.DateField()

    def __str__(self):
        return f"{self.quantity_kg}kg of {self.feed_type} for {self.livestock.tag_id}"


class YieldRecord(models.Model):
    livestock = models.ForeignKey(
        Livestock, related_name="yield_records", on_delete=models.CASCADE
    )
    yield_type = models.CharField(max_length=50, help_text="e.g., Milk, Eggs")
    quantity = models.DecimalField(max_digits=7, decimal_places=2)
    unit = models.CharField(max_length=20, help_text="e.g., Liters, Units")
    date = models.DateField()

    def __str__(self):
        return f"{self.quantity} {self.unit} of {self.yield_type} from {self.livestock.tag_id}"

