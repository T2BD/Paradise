# booking/management/commands/billing_maintenance.py
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.core.mail import send_mail
from booking.models import Booking

REMIND_AFTER_DAYS = 2
AUTO_CANCEL_AFTER_DAYS = 5

class Command(BaseCommand):
    help = "Send payment reminder emails and auto-cancel very overdue unpaid bookings."

    def handle(self, *args, **options):
        today = now()
        reminded = 0
        cancelled = 0

        # Remind unpaid bookings older than REMIND_AFTER_DAYS
        remind_cutoff = today - timedelta(days=REMIND_AFTER_DAYS)
        to_remind = Booking.objects.filter(
            payment_status="unpaid",
            created_at__lte=remind_cutoff
        )
        for b in to_remind:
            if b.customer_email:
                send_mail(
                    subject=f"Payment Reminder — {b.invoice_number}",
                    message=(
                        f"Dear {b.customer_name},\n\n"
                        f"This is a friendly reminder to complete payment for your booking "
                        f"(Invoice {b.invoice_number}). You can pay from your portal or contact us.\n\n"
                        f"Thank you."
                    ),
                    from_email="noreply@paradisehotel.com",
                    recipient_list=[b.customer_email],
                    fail_silently=True,
                )
                reminded += 1

        # Auto-cancel unpaid bookings older than AUTO_CANCEL_AFTER_DAYS
        cancel_cutoff = today - timedelta(days=AUTO_CANCEL_AFTER_DAYS)
        to_cancel = Booking.objects.filter(
            payment_status="unpaid",
            created_at__lte=cancel_cutoff
        )
        for b in to_cancel:
            b.status = "cancelled"
            b.save(update_fields=["status"])
            cancelled += 1

        self.stdout.write(self.style.SUCCESS(
            f"Reminded: {reminded}, Auto-cancelled: {cancelled}"
        ))
