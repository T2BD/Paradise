# booking/admin.py
import io
import base64
import datetime
import matplotlib.pyplot as plt
import csv

from django.http import HttpResponse
from django.db.models import Count, Sum, Avg, F, ExpressionWrapper, DurationField
from django.utils.html import format_html
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.template.loader import render_to_string
from weasyprint import HTML   # ✅ Use WeasyPrint only

from .models import Room, Booking


# --- Inline Booking inside Room ---
class BookingInline(admin.TabularInline):
    model = Booking
    extra = 1
    fields = ("customer_name", "check_in", "check_out")
    readonly_fields = ("created_at",)
    show_change_link = True


# =========================================
# Custom Admin Site with Dashboard
# =========================================
class CustomAdminSite(admin.AdminSite):
    site_header = "Paradise Hotel Admin"
    site_title = "Paradise Admin"
    index_title = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_view(self.dashboard_view)),
        ]
        return custom_urls + urls

    # ✅ Override the main /admin/ homepage
    def index(self, request, extra_context=None):
        return self.dashboard_view(request)

    def dashboard_view(self, request):
        today = timezone.now().date()

        # --- Stats ---
        total_rooms = Room.objects.count()

        # --- Filters from request ---
        start = request.GET.get("start")
        end = request.GET.get("end")
        room_type = request.GET.get("room_type")

        # --- Handle quick filters safely ---
        if not start and not end:
            # show last 30 days by default
            start = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            end = today.strftime("%Y-%m-%d")
        elif start and not end:
            end = today.strftime("%Y-%m-%d")
        elif end and not start:
            start = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

        # Apply filters
        bookings_qs = Booking.objects.select_related("room").filter(
            created_at__date__gte=start,
            created_at__date__lte=end
        )
        if room_type:
            bookings_qs = bookings_qs.filter(room__room_type=room_type)

        # --- Updated stats (filtered) ---
        total_bookings = bookings_qs.count()
        today_checkins = bookings_qs.filter(check_in=today).count()
        today_checkouts = bookings_qs.filter(check_out=today).count()

        # --- Weekly bookings data ---
        last_week = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%b %d") for d in last_week]
        data = [bookings_qs.filter(created_at__date=d).count() for d in last_week]

        # --- Bar chart: Bookings per Room Type ---
        room_type_data = (
            bookings_qs.values("room__room_type")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        room_labels = [entry["room__room_type"] for entry in room_type_data]
        room_counts = [entry["total"] for entry in room_type_data]

        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.bar(room_labels, room_counts, color="#198754")
        ax2.set_title("🏨 Bookings per Room Type", fontsize=14, fontweight="bold")
        ax2.set_ylabel("Number of Bookings")
        ax2.set_xlabel("Room Type")
        plt.xticks(rotation=20)
        buffer2 = io.BytesIO()
        plt.tight_layout()
        fig2.savefig(buffer2, format="png", transparent=True)
        buffer2.seek(0)
        room_chart_base64 = base64.b64encode(buffer2.read()).decode("utf-8")
        buffer2.close()

        # --- Weekly line chart ---
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(labels, data, marker="o", color="#0dcaf0", linewidth=2)
        ax.fill_between(labels, data, color="#0dcaf0", alpha=0.25)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.set_title("📈 Weekly Bookings", fontsize=14, fontweight="bold", color="white")
        ax.set_ylabel("Bookings", color="white")
        ax.set_xlabel("Date", color="white")
        plt.xticks(rotation=30, color="white", fontsize=9)
        plt.yticks(color="white", fontsize=9)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none")
        buffer = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buffer, format="png", transparent=True)
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        buffer.close()

        # --- Revenue per Room Type ---
        revenue_per_type = (
            bookings_qs.values("room__room_type")
            .annotate(total_revenue=Sum("room__price"))
            .order_by("-total_revenue")
        )

        # --- Daily Revenue Trend ---
        revenue_data = (
            bookings_qs.values("check_in")
            .annotate(total=Sum("room__price"))
            .order_by("check_in")
        )

        revenue_labels = [r["check_in"].strftime("%b %d") for r in revenue_data if r["check_in"]]
        revenue_totals = [r["total"] for r in revenue_data if r["check_in"]]

        fig4, ax4 = plt.subplots(figsize=(7, 4))
        ax4.plot(revenue_labels, revenue_totals, marker="o", color="#28a745", linewidth=2)
        ax4.fill_between(revenue_labels, revenue_totals, color="#28a745", alpha=0.25)
        ax4.set_title("💰 Revenue Trend (Daily)", fontsize=14, fontweight="bold")
        ax4.set_ylabel("Revenue ($)")
        plt.xticks(rotation=30)
        ax4.grid(True, linestyle="--", alpha=0.4)

        buffer4 = io.BytesIO()
        plt.tight_layout()
        fig4.savefig(buffer4, format="png", transparent=True)
        buffer4.seek(0)
        revenue_chart_base64 = base64.b64encode(buffer4.read()).decode("utf-8")
        buffer4.close()

        # --- Average Stay Duration (in days) ---
        avg_stay = bookings_qs.annotate(
            stay_length=ExpressionWrapper(F("check_out") - F("check_in"), output_field=DurationField())
        ).aggregate(avg_days=Avg("stay_length"))
        avg_stay_days = (avg_stay["avg_days"].days if avg_stay["avg_days"] else 0)

        # --- Occupancy Rate ---
        booked_days = sum(
            [(b.check_out - b.check_in).days for b in bookings_qs if b.check_out and b.check_in]
        )
        days_span = 30
        total_room_days = Room.objects.count() * days_span
        occupancy_rate = round((booked_days / total_room_days) * 100, 2) if total_room_days else 0

        # --- Occupancy Pie Chart ---
        fig3, ax3 = plt.subplots(figsize=(5, 5))
        labels_pie = ["Booked", "Available"]
        values_pie = [booked_days, total_room_days - booked_days]
        colors = ["#0d6efd", "#6c757d"]
        ax3.pie(values_pie, labels=labels_pie, autopct="%1.1f%%", startangle=140, colors=colors)
        ax3.set_title("🏨 Occupancy Rate (30 days)", fontsize=14, fontweight="bold")
        fig3.patch.set_alpha(0.0)
        ax3.set_facecolor("none")
        buffer3 = io.BytesIO()
        plt.tight_layout()
        fig3.savefig(buffer3, format="png", transparent=True)
        buffer3.seek(0)
        occupancy_chart_base64 = base64.b64encode(buffer3.read()).decode("utf-8")
        buffer3.close()

        # ✅ CSV export
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=bookings.csv"
            writer = csv.writer(response)
            writer.writerow(["Customer", "Room", "Check-in", "Check-out", "Created At"])
            for b in bookings_qs:
                writer.writerow([
                    b.customer_name,
                    b.room.room_number,
                    b.check_in,
                    b.check_out,
                    b.created_at,
                ])
            return response

        # ✅ PDF export
        if request.GET.get("export") == "pdf":
            html_string = render_to_string("admin/pdf_report.html", {
                "bookings": bookings_qs,
                "total_rooms": total_rooms,
                "total_bookings": total_bookings,
                "today_checkins": today_checkins,
                "today_checkouts": today_checkouts,
                "revenue_per_type": revenue_per_type,
                "avg_stay_days": avg_stay_days,
                "occupancy_rate": occupancy_rate,
                "chart": chart_base64,
                "room_chart": room_chart_base64,
                "occupancy_chart": occupancy_chart_base64,
            })
            pdf_file = HTML(string=html_string).write_pdf()
            response = HttpResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = "attachment; filename=bookings_report.pdf"
            return response

        # --- Top 3 rooms & recent bookings ---
        top_rooms = (
            bookings_qs.values("room__room_number", "room__room_type")
            .annotate(total_bookings=Count("id"))
            .order_by("-total_bookings")[:3]
        )
        recent_bookings = bookings_qs.order_by("-created_at")[:5]

        # --- Context for dashboard ---
        context = dict(
            self.each_context(request),
            total_rooms=total_rooms,
            total_bookings=total_bookings,
            today_checkins=today_checkins,
            today_checkouts=today_checkouts,
            chart=chart_base64,
            room_chart=room_chart_base64,
            occupancy_chart=occupancy_chart_base64,  # ⬅️ new chart
            top_rooms=top_rooms,
            recent_bookings=recent_bookings,
            revenue_per_type=revenue_per_type,
            avg_stay_days=avg_stay_days,
            occupancy_rate=occupancy_rate,
            revenue_chart=revenue_chart_base64
        )
        return TemplateResponse(request, "admin/dashboard.html", context)


# ✅ Register custom admin site
custom_admin_site = CustomAdminSite(name="custom_admin")


# --- Room Admin ---
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "price", "status_badge", "preview_image")
    search_fields = ("room_number", "room_type")
    list_filter = ("room_type", "status")
    inlines = [BookingInline]

    def status_badge(self, obj):
        color_map = {"available": "green", "booked": "red", "maintenance": "orange"}
        color = color_map.get(obj.status, "gray")
        return format_html(
            '<span style="padding:4px 8px; border-radius:6px; color:white; background-color:{};">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="40" style="object-fit:cover;" />',
                obj.image.url,
            )
        return "No Image"
    preview_image.short_description = "Image"


# --- Booking Admin ---
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "room", "check_in", "check_out", "created_at", "user")
    list_filter = ("check_in", "check_out", "room__room_type")
    search_fields = ("customer_name", "room__room_number", "user__username", "user__email")
    ordering = ("-created_at",)
