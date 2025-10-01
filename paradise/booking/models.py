from django.db import models
from django.contrib.auth.models import User   # built-in user model


# ========================
# Room Model
# ========================
class Room(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("booked", "Booked"),
        ("maintenance", "Maintenance"),
    ]

    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="rooms/", blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available"
    )

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type})"


# ========================
# Booking Model
# ========================
BOOKING_SOURCES = [
    ("walk_in", "Walk-in"),
    ("website", "Website"),
    ("agent", "Travel Agent"),
    ("corporate", "Corporate"),
]

class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    customer_name = models.CharField(max_length=100)
    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ new field to track how booking was made
    source = models.CharField(
        max_length=20,
        choices=BOOKING_SOURCES,
        default="website"
    )

    def __str__(self):
        return f"Booking by {self.customer_name} for {self.room}"
