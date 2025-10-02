from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

# Create or ensure a staff/superuser for testing
User = get_user_model()
if not User.objects.filter(username="debugadmin").exists():
    u = User.objects.create_user(username="debugadmin", email="debug@local", password="debugpw")
    u.is_staff = True
    u.is_superuser = True
    u.save()
else:
    u = User.objects.get(username="debugadmin")
    u.is_staff = True
    u.is_superuser = True
    u.set_password("debugpw")
    u.save()

c = Client()
c.force_login(u)

resp = c.get("/admin/")
print("STATUS:", resp.status_code)
body = resp.content.decode("utf-8", errors="replace")
print("--- BEGIN RESPONSE (first 4000 chars) ---")
print(body[:4000])
print("--- END RESPONSE ---")
