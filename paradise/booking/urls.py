# booking/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public / site pages
    path("", views.home, name="home"),
    path("rooms/", views.room_list, name="room_list"),
    path("rooms/<int:pk>/", views.room_detail, name="room_detail"),
    path("book/", views.book_room, name="book_room"),

    # Existing booking utilities
    path("booking/<int:booking_id>/invoice/", views.download_invoice, name="download_invoice"),
    path("booking/<int:booking_id>/paypal-start/", views.start_payment, name="paypal_start"),
    path("booking/<int:booking_id>/paypal-success/", views.paypal_success, name="paypal_success"),
    path("booking/<int:booking_id>/paypal-cancel/", views.paypal_cancel, name="paypal_cancel"),
    path("booking/<int:booking_id>/refund/", views.process_refund, name="process_refund"),

    # ✅ Step 14: Customer Portal
    path("portal/bookings/", views.portal_bookings, name="portal_bookings"),

    # ✅ Step 14: Staff Finance Dashboard + CSV
    path("staff/finance/", views.staff_finance, name="staff_finance"),
    path("staff/finance/export/csv/", views.finance_csv, name="finance_csv"),
]
