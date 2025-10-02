from django.urls import path
from . import views

# --- Booking app URL patterns ---
urlpatterns = [
    path("", views.home, name="home"),  # ✅ homepage
    path("rooms/", views.room_list, name="room_list"),
    path("book/", views.book_room, name="book_room"),
    path("signup/", views.signup, name="signup"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("booking/<int:pk>/invoice/", views.booking_invoice, name="booking_invoice"),

    path("<int:booking_id>/paypal/", views.start_payment, name="paypal_start"),
    path("<int:booking_id>/paypal-success/", views.payment_success, name="paypal_success"),
    path("<int:booking_id>/paypal-cancel/", views.payment_cancel, name="paypal_cancel"),


]

# --- End URL patterns ---
