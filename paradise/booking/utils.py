# booking/utils.py
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import weasyprint
import tempfile

def send_booking_confirmation(booking):
    """Send booking confirmation email with PDF invoice attached."""
    subject = f"Your Paradise Hotel Booking Confirmation (#{booking.id})"
    body = render_to_string("booking/email_confirmation.txt", {"booking": booking})

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.customer_email],
    )

    # Render PDF invoice from template
    html = render_to_string("booking/invoice.html", {"booking": booking})
    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    weasyprint.HTML(string=html).write_pdf(pdf_file.name)

    # Attach PDF
    email.attach_file(pdf_file.name, mimetype="application/pdf")
    email.send()
