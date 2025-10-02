# booking/tests/test_dashboard.py
from decimal import Decimal
import datetime

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from booking.models import Room, Booking

User = get_user_model()

# Ensure testserver is allowed so Client() requests succeed
@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class DashboardSmokeTests(TestCase):
    def setUp(self):
        # create a staff / superuser for tests
        self.user = User.objects.create_user(username="testadmin", email="test@local", password="pw")
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        self.client = Client()
        self.client.force_login(self.user)

        # create a Room with concrete values (price must be Decimal)
        self.room = Room.objects.create(
            room_number="101",
            room_type="Single",          # adjust to a valid choice if your model restricts choices
            price=Decimal("100.00"),     # Decimal for DecimalField
            status="available",          # adjust to a valid choice for your model
        )

        # create a booking so dashboard shows something
        today = timezone.now().date()
        Booking.objects.create(
            customer_name="Test Customer",
            room=self.room,
            check_in=today,
            check_out=today + datetime.timedelta(days=1),
            created_at=timezone.now(),
            # if your Booking model requires user/source fields, add them (user=self.user, source="web", ...)
        )

    def test_admin_dashboard_loads(self):
        """Dashboard should return 200 for logged-in staff user and contain expected header text."""
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        # checks that your custom dashboard includes the heading text
        self.assertContains(resp, "Paradise Hotel", msg_prefix="Dashboard should include site heading")

    def test_csv_export(self):
        """CSV export endpoint should return CSV content for the filtered bookings queryset."""
        resp = self.client.get("/admin/?export=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        body = resp.content.decode("utf-8", errors="ignore")
        # header "Customer" should be present in CSV output first line
        first_line = body.splitlines()[0] if body else ""
        self.assertIn("Customer", first_line)
