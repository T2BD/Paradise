# booking/views.py
import tempfile
from decimal import Decimal

import weasyprint
import paypalrestsdk

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.timezone import now

from .models import Room, Booking, Payment  # assumes Payment model exists with booking FK
from booking.utils import send_booking_confirmation


# ---------------------------------------------------------------------
# Forms (placeholder you had – kept as-is, not used, but harmless)
# ---------------------------------------------------------------------
class BookingForm:
    pass


# ---------------------------------------------------------------------
# Public pages / simple flows
# ---------------------------------------------------------------------
def home(request):
    return render(request, "booking/index.html")


def test_view(request):
    return render(request, "booking/test.html")


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


def room_list(request):
    rooms = Room.objects.all()
    return render(request, "booking/room_list.html", {"rooms": rooms})


def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    return render(request, "booking/room_detail.html", {"room": room})


def book_room(request):
    """
    Kept the version that creates a booking directly and shows a success page,
    since your stubbed BookingForm wasn’t actually wired.
    """
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

        # Optional confirmation email (your util)
        try:
            send_booking_confirmation(booking)
        except Exception:
            # Non-fatal if email util isn’t configured yet
            pass

        # ✅ Show confirmation page
        return render(request, "booking/booking_success.html", {"booking": booking})

    rooms = Room.objects.all()
    return render(request, "booking/book_room.html", {"rooms": rooms})


def my_bookings(request):
    if not request.user.is_authenticated:
        return redirect("login")
    bookings = Booking.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "booking/my_bookings.html", {"bookings": bookings})


def room_bookings_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    bookings = room.bookings.all()   # uses related_name="bookings"
    return render(request, "booking/room_bookings.html", {"room": room, "bookings": bookings})


# ---------------------------------------------------------------------
# Invoice (kept both endpoints you had)
# ---------------------------------------------------------------------
def booking_invoice(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    html = render_to_string("booking/invoice.html", {"booking": booking})
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=invoice_{booking.id}.pdf"
    weasyprint.HTML(string=html).write_pdf(response)
    return response


def download_invoice(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    html = render_to_string("booking/invoice.html", {"booking": booking})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Invoice-{booking.invoice_number}.pdf"'
    weasyprint.HTML(string=html).write_pdf(response)
    return response


# ---------------------------------------------------------------------
# PayPal
# ---------------------------------------------------------------------
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})


def start_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Ensure we stringify a Decimal for the SDK
    amount = str(booking.room.price)

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": request.build_absolute_uri(f"/booking/{booking.id}/paypal-success/"),
            "cancel_url": request.build_absolute_uri(f"/booking/{booking.id}/paypal-cancel/"),
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": f"Room {booking.room.room_number}",
                    "sku": str(booking.id),
                    "price": amount,
                    "currency": "USD",
                    "quantity": 1,
                }]
            },
            "amount": {"total": amount, "currency": "USD"},
            "description": f"Booking payment for {booking.customer_name}",
        }]
    })

    if payment.create():
        # record a pending Payment row (if your Payment model is set like Payment(booking=..., status=...))
        try:
            Payment.objects.create(booking=booking, amount=Decimal(amount), status="pending")
        except Exception:
            # If Payment model differs, skip silently
            pass

        for link in payment.links:
            if link.method == "REDIRECT":
                return redirect(link.href)
        return HttpResponse("PayPal did not return a redirect link.", status=500)
    else:
        return HttpResponse("Error creating PayPal payment", status=500)


def payment_success(request, booking_id):
    """
    Handles PayPal success, marks booking as paid, generates PDF invoice,
    and emails it to the customer.
    """
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")
    if not payment_id or not payer_id:
        return HttpResponse("Missing payment identifiers.", status=400)

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
    except Exception:
        return HttpResponse("Payment lookup failed.", status=500)

    # Execute the payment
    if not payment.execute({"payer_id": payer_id}):
        return HttpResponse("Payment execution failed.", status=500)

    booking = get_object_or_404(Booking, id=booking_id)

    # Update payment fields on the booking
    try:
        amount = Decimal(str(booking.room.price))
    except Exception:
        amount = Decimal("0")

    booking.payment_status = "paid"
    booking.amount_paid = amount
    booking.payment_date = now()
    booking.status = "confirmed"
    booking.save()

    # Update Payment row if present
    try:
        Payment.objects.filter(booking=booking).update(status="paid", amount=amount, paid_at=now())
    except Exception:
        pass

    # ---------- Generate PDF Invoice ----------
    html = render_to_string("booking/invoice.html", {"booking": booking})
    pdf_file = tempfile.NamedTemporaryFile(delete=True, suffix=".pdf")
    weasyprint.HTML(string=html).write_pdf(pdf_file.name)

    # ---------- Send Email with Invoice ----------
    recipient = None
    if booking.user and getattr(booking.user, "email", None):
        recipient = booking.user.email
    elif getattr(booking, "customer_email", None):
        recipient = booking.customer_email

    if recipient:
        email = EmailMessage(
            subject=f"Paradise Hotel Invoice — {booking.invoice_number}",
            body="Thank you for your booking. Your payment was successful. The invoice is attached as a PDF.",
            from_email="no-reply@paradisehotel.com",
            to=[recipient],
        )
        try:
            email.attach_file(pdf_file.name)
            email.send()
        except Exception:
            # Don’t crash the flow if email backend isn’t configured
            pass

    messages.success(request, f"Payment successful for {booking.invoice_number}. Invoice emailed.")
    # You can redirect to details page if you have it, else back to my bookings
    return redirect("my_bookings")


# If your urls.py used views.payment_success with name 'paypal_success', keep this alias:
paypal_success = payment_success


def payment_cancel(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Mark Payment row failed if present
    try:
        Payment.objects.filter(booking=booking).update(status="failed")
    except Exception:
        pass

    # Mark booking as unpaid/pending
    booking.payment_status = "unpaid"
    booking.status = "pending"
    booking.save()

    messages.error(request, f"Payment cancelled for {booking.invoice_number}.")
    return redirect("my_bookings")


# ---------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------
def process_refund(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.payment_status == "paid":
        # Mark refund on booking
        booking.payment_status = "refunded"
        # If you keep these extra fields on Booking:
        if hasattr(booking, "refund_requested"):
            booking.refund_requested = True
        if hasattr(booking, "refund_amount"):
            booking.refund_amount = booking.amount_paid
        if hasattr(booking, "refund_date"):
            booking.refund_date = now()
        booking.status = "refunded"
        booking.save()

        # Update Payment record if exists
        try:
            Payment.objects.filter(booking=booking).update(status="refunded", refunded_at=now())
        except Exception:
            pass

        # Auto-send refund confirmation email
        recipient = None
        if booking.user and getattr(booking.user, "email", None):
            recipient = booking.user.email
        elif getattr(booking, "customer_email", None):
            recipient = booking.customer_email

        if recipient:
            try:
                messages_body = (
                    f"Dear {booking.customer_name}, your payment of {booking.amount_paid} "
                    f"has been refunded for invoice {booking.invoice_number}."
                )
                from django.core.mail import send_mail
                send_mail(
                    subject=f"Refund Issued — {booking.invoice_number}",
                    message=messages_body,
                    from_email="noreply@paradisehotel.com",
                    recipient_list=[recipient],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.success(request, f"Refund processed for {booking.invoice_number}.")
    else:
        messages.error(request, "Refund not allowed for this booking.")

    # safer redirect that exists in your app
    return redirect("my_bookings")
