from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Use the custom admin site we made
from booking.admin import custom_admin_site

urlpatterns = [
    # ✅ Custom Admin (replaces default admin)
    path("admin/", custom_admin_site.urls),

    # Booking app URLs (homepage, rooms, booking)
    path("", include("booking.urls")),

    # Django auth system (login/logout/password reset)
    path("accounts/", include("django.contrib.auth.urls")),
]

# ✅ Serve media (room images) + static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
