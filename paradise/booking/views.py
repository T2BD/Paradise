# booking/views.py
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .models import Room, Booking
from .models import Booking




# --- View: List all rooms ---

def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'booking/room_list.html', {'rooms': rooms})
# --- End room_list ---




# --- View: Create a booking ---

def book_room(request):
    if request.method == "POST":
        room_id = request.POST.get("room_id")
        customer = request.POST.get("customer_name")
        checkin = request.POST.get("check_in")
        checkout = request.POST.get("check_out")

        booking = Booking.objects.create(
            room=Room.objects.get(id=room_id),
            customer_name=customer,
            check_in=checkin,
            check_out=checkout,
        )

        # ✅ Instead of redirect, show confirmation page
        return render(request, "booking/booking_success.html", {"booking": booking})

    rooms = Room.objects.all()
    return render(request, "booking/book_room.html", {"rooms": rooms})

# --- End book_room ---


def my_bookings(request):
    if not request.user.is_authenticated:
        return redirect("login")  # send unauthenticated users to login
    bookings = Booking.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "booking/my_bookings.html", {"bookings": bookings})

# ==================================================================================================


def test_view(request):
    return render(request, "booking/test.html")

# =============================================================


def home(request):
    return render(request, "booking/index.html")

# ==============================================================


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto-login after signup
            return redirect("room_list")
    else:
        form = UserCreationForm()
    return render(request, "booking/signup.html", {"form": form})

# ====================================================================================

