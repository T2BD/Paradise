# booking/views.py
import tempfile

import weasyprint
import paypalrestsdk


from django.conf import settings
from django.core.mail import EmailMessage

from .models import Booking, Payment
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



def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    return render(request, "booking/room_detail.html", {"room": room})



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

#
def room_bookings_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    bookings = room.bookings.all()   # ✅ use related_name
    return render(request, "booking/room_bookings.html", {"room": room, "bookings": bookings})


#



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



paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

def start_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    amount = str(booking.room.price)

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": request.build_absolute_uri(f"/booking/{booking.id}/paypal-success/"),
            "cancel_url": request.build_absolute_uri(f"/booking/{booking.id}/paypal-cancel/")
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": f"Room {booking.room.room_number}",
                    "sku": str(booking.id),
                    "price": amount,
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {"total": amount, "currency": "USD"},
            "description": f"Booking payment for {booking.customer_name}"
        }]
    })

    if payment.create():
        Payment.objects.create(booking=booking, amount=amount, status="pending")
        for link in payment.links:
            if link.method == "REDIRECT":
                return redirect(link.href)
    else:
        return HttpResponse("Error creating PayPal payment", status=500)


def paypal_success(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        # ✅ Example: retrieve booking from session or db
        booking_id = request.session.get("booking_id")
        booking = Booking.objects.get(id=booking_id)

        # ---------- Generate PDF Invoice ----------
        html = render_to_string("booking/invoice.html", {"booking": booking})
        pdf_file = tempfile.NamedTemporaryFile(delete=True, suffix=".pdf")
        weasyprint.HTML(string=html).write_pdf(pdf_file.name)

        # ---------- Send Email with Invoice ----------
        email = EmailMessage(
            subject=f"Paradise Hotel Invoice — {booking.invoice_number}",
            body="Thank you for your booking. Attached is your invoice PDF.",
            from_email="no-reply@paradisehotel.com",
            to=[booking.user.email if booking.user else booking.customer_email],
        )
        email.attach_file(pdf_file.name)
        email.send()

        return HttpResponse("Payment successful, invoice emailed!")
    else:
        return HttpResponse("Payment failed.")


def payment_cancel(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.payment.status = "failed"
    booking.payment.save()
    return HttpResponse("Payment cancelled ❌")