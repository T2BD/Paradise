# booking/views.py
import weasyprint




from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.checks import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string

from .models import Room, Booking
from .models import Booking
from booking.utils import send_booking_confirmation


class BookingForm:
    pass


def book_room(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save()
            send_booking_confirmation(booking)
            messages.success(request, "Booking successful! Confirmation sent to your email.")
            return redirect("booking_success", pk=booking.pk)


#
def booking_invoice(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    html = render_to_string("booking/invoice.html", {"booking": booking})
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=invoice_{booking.id}.pdf"
    weasyprint.HTML(string=html).write_pdf(response)
    return response



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

