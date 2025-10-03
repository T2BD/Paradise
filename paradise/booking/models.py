import tempfile

import weasyprint
from django.core.mail import EmailMessage
from django.db import models
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.timezone import now




def send_invoice_email(booking):
    html = render_to_string("booking/invoice.html", {"booking": booking})
    pdf_file = tempfile.NamedTemporaryFile(delete=True, suffix=".pdf")
    weasyprint.HTML(string=html).write_pdf(pdf_file.name)

    email = EmailMessage(
        subject=f"Paradise Hotel - Invoice {booking.invoice_number}",
        body="Please find your updated invoice attached.",
        from_email="no-reply@paradisehotel.com",
        to=[booking.customer_email],
    )
    email.attach_file(pdf_file.name)
    email.send()




# ========================
# Room Model
# ========================
class Room(models.Model):
    ROOM_STATUS = [
        ("available", "Available"),
        ("booked", "Booked"),
        ("maintenance", "Maintenance"),
    ]

    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="rooms/", blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=ROOM_STATUS,
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

BOOKING_STATUS = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("cancelled", "Cancelled"),
    ("refunded", "Refunded"),
]


class Booking(models.Model):
    room = models.ForeignKey(
        "Room",
        on_delete=models.CASCADE,
        related_name="bookings"   # ✅ no clash with "room"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField(blank=True, null=True)

    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Booking metadata
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default="pending")
    source = models.CharField(max_length=20, choices=BOOKING_SOURCES, default="website")

    # Refund fields
    refund_requested = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_date = models.DateTimeField(null=True, blank=True)

    # ✅ Invoice number (auto-generated)
    invoice_number = models.CharField(max_length=20, unique=True, blank=True)

    # ✅ Payment tracking
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
        ],
        default="unpaid"
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # auto-generate invoice number if not set
        if not self.invoice_number:
            year = now().year
            count = Booking.objects.filter(created_at__year=year).count() + 1
            self.invoice_number = f"INV-{year}-{count:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name} ({self.status}, {self.payment_status})"


class Payment(models.Model):
    booking = models.OneToOneField("Booking", on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, default="pending")  # pending, success, failed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id or 'N/A'} - {self.status}"




