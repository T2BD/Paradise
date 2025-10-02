# booking/tests/test_dashboard.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from booking.models import Room, Booking
from django.utils import timezone
import datetime

class TestDashboard(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            "testadmin", "test@example.com", "password"
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.room = Room.objects.create(
            room_number="101",
            room_type="Single",
            price=100.00,   # ✅ keep only fields that exist in your Room model
        )

        Booking.objects.create(
            room=self.room,
            customer_name="Alice",
            check_in=timezone.now().date(),
            check_out=timezone.now().date() + datetime.timedelta(days=2),
        )

    def test_admin_dashboard_loads(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Paradise Hotel", resp.content)

    def test_csv_export(self):
        resp = self.client.get("/admin/?export=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("Customer", resp.content.decode())
