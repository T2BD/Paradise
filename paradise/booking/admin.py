# booking/admin.py
import io
import csv
import base64
import datetime
import matplotlib
matplotlib.use("Agg")   # use non-GUI backend so matplotlib won't try to use Tkinter
import matplotlib.pyplot as plt

from django.http import HttpResponse
from django.db.models import Count, Sum, Avg, F, ExpressionWrapper, DurationField
from django.utils.html import format_html
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.template.loader import render_to_string
from weasyprint import HTML   # ✅ Use WeasyPrint only
from django.core.cache import cache
from .models import Room, Booking


# --- SVG helpers (left in place for future use) ---
def svg_bar(labels, values, title="", width=600, height=300, bar_color="#0d6efd"):
    if not labels:
        return "<svg></svg>"
    max_v = max(values) or 1
    padding = 20
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding
    bar_w = inner_w / (len(values) * 1.5)
    gap = bar_w / 2
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">'
    ]
    if title:
        svg_parts.append(f'<title>{title}</title>')
        svg_parts.append(
            f'<text x="{width/2}" y="16" text-anchor="middle" font-size="14" fill="#ffffff" style="font-family:Arial">{title}</text>'
        )
    svg_parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="none"/>')
    svg_parts.append(
        f'<line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" stroke="#ccc" stroke-width="1"/>'
    )

    cur_x = padding + gap / 2
    for lab, val in zip(labels, values):
        h = (val / max_v) * (inner_h - 30)
        y = (height - padding) - h
        rect = (
            f'<g>'
            f'<rect x="{cur_x}" y="{y}" width="{bar_w}" height="{h}" fill="{bar_color}" '
            f'style="rx:4; stroke:none;">'
            f'<animate attributeName="height" from="0" to="{h}" dur="600ms" fill="freeze" />'
            f'<animate attributeName="y" from="{height-padding}" to="{y}" dur="600ms" fill="freeze" />'
            f'</rect>'
            f'<title>{lab}: {val}</title>'
            f'</g>'
        )
        svg_parts.append(rect)
        svg_parts.append(
            f'<text x="{cur_x + bar_w/2}" y="{height - padding + 14}" font-size="11" text-anchor="middle" fill="#ffffff" style="font-family:Arial">{lab}</text>'
        )
        cur_x += bar_w + gap

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def svg_line(labels, values, title="", width=700, height=300, stroke="#0dcaf0"):
    if not labels:
        return "<svg></svg>"
    max_v = max(values) or 1
    padding = 30
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding
    pts = []
    for i, v in enumerate(values):
        x = padding + (i * (inner_w / max(1, (len(values) - 1))))
        y = padding + (inner_h - (v / max_v) * inner_h)
        pts.append((x, y))
    poly_pts = " ".join(f"{x},{y}" for x, y in pts)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">'
    ]
    if title:
        svg.append(f'<title>{title}</title>')
        svg.append(
            f'<text x="{width/2}" y="16" text-anchor="middle" font-size="14" fill="#ffffff" style="font-family:Arial">{title}</text>'
        )
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="none"/>')
    svg.append(f'<polyline points="{poly_pts}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">')
    svg.append('<animate attributeName="stroke-dashoffset" from="1000" to="0" dur="800ms" fill="freeze" />')
    svg.append("</polyline>")

    for (x, y), lab, v in zip(pts, labels, values):
        svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{stroke}">')
        svg.append(f"<title>{lab}: {v}</title>")
        svg.append("</circle>")
        svg.append(
            f'<text x="{x}" y="{height - padding + 14}" text-anchor="middle" font-size="11" fill="#ffffff" style="font-family:Arial">{lab}</text>'
        )
    svg.append("</svg>")
    return "".join(svg)


def fig_to_base64(fig):
    """Save a Matplotlib figure to base64 and close it (prevents GUI & memory leaks)."""
    buf = io.BytesIO()
    try:
        fig.tight_layout()
    except Exception:
        pass
    fig.savefig(buf, format="png", transparent=True)
    buf.seek(0)
    s = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    buf.close()
    return s


def fig_to_svg(fig, inject_tag=None, values=None):
    """Save fig as SVG string (does not fail if tight_layout errors)."""
    buf = io.BytesIO()
    try:
        fig.tight_layout()
    except Exception:
        pass
    fig.savefig(buf, format="svg")
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    # do not close fig here in case caller wants to reuse it (we'll close in fig_to_base64 if used)
    buf.close()
    if inject_tag and values:
        parts = svg.split(f"<{inject_tag} ")
        out = parts[0]
        i = 0
        for p in parts[1:]:
            if i < len(values):
                idx = p.find("/>")
                if idx != -1:
                    out += f"<{inject_tag} " + p[:idx] + f">" + f"<title>{values[i]}</title>" + p[idx + 2:]
                else:
                    out += f"<{inject_tag} " + p
            else:
                out += f"<{inject_tag} " + p
            i += 1
        svg = out
    return svg


def apply_dark_style(ax, fig):
    """Apply dashboard dark styling to a Matplotlib Axes/Figure."""
    ax.set_facecolor("#1e3c72")
    fig.patch.set_facecolor("#1e3c72")
    for spine in ax.spines.values():
        spine.set_color("white")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")


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
        custom_urls = [path("dashboard/", self.admin_view(self.dashboard_view))]
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

        # parse incoming date strings to date objects safely
        def parse_date_or_default(s, default):
            if not s:
                return default
            try:
                return datetime.date.fromisoformat(s)
            except Exception:
                try:
                    return datetime.datetime.strptime(s, "%Y-%m-%d").date()
                except Exception:
                    return default

        # --- Handle quick filters safely: default last 30 days ---
        if not start and not end:
            start_date = today - datetime.timedelta(days=30)
            end_date = today
        elif start and not end:
            start_date = parse_date_or_default(start, today - datetime.timedelta(days=30))
            end_date = today
        elif end and not start:
            end_date = parse_date_or_default(end, today)
            start_date = today - datetime.timedelta(days=30)
        else:
            start_date = parse_date_or_default(start, today - datetime.timedelta(days=30))
            end_date = parse_date_or_default(end, today)

        # Ensure start_date <= end_date
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        # --- Safe defaults so template never errors if a chart wasn't created ---
        chart_base64 = chart_svg = ""
        room_chart_base64 = room_chart_svg = ""
        occupancy_chart_base64 = revenue_chart_base64 = source_chart_base64 = ""

        # lightweight cache helper (uses Django cache; production: use redis/memcached)
        from django.core.cache import cache
        def cached_chart(key, make_func, timeout=300):
            val = cache.get(key)
            if val is not None:
                return val
            val = make_func()
            if val:
                cache.set(key, val, timeout)
            return val

        # Apply filters
        bookings_qs = Booking.objects.select_related("room").filter(
            created_at__date__gte=start_date, created_at__date__lte=end_date
        )
        if room_type:
            bookings_qs = bookings_qs.filter(room__room_type=room_type)

        # --- Updated stats (filtered) ---
        total_bookings = bookings_qs.count()
        today_checkins = bookings_qs.filter(check_in=today).count()
        today_checkouts = bookings_qs.filter(check_out=today).count()

        # --- Weekly bookings data (last 7 days up to end_date) ---
        last_week = [end_date - datetime.timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%b %d") for d in last_week]
        data = [bookings_qs.filter(created_at__date=d).count() for d in last_week]


        # --- Bar chart: Bookings per Room Type ---
        room_type_data = bookings_qs.values("room__room_type").annotate(total=Count("id")).order_by("-total")
        room_labels = [entry["room__room_type"] for entry in room_type_data]
        room_counts = [entry["total"] for entry in room_type_data]

        # --- SVG fallbacks (non-JS interactive charts) ---
        chart_svg = ""
        room_chart_svg = ""
        try:
            if labels and any(data):
                chart_svg = svg_line(labels, data, title="Weekly Bookings")
            if room_labels and any(room_counts):
                room_chart_svg = svg_bar(room_labels, room_counts, title="Bookings per Room Type")
        except Exception:
            # keep fallbacks empty on error; PNGs will still be used for PDF/export
            chart_svg = chart_svg or ""
            room_chart_svg = room_chart_svg or ""

        # draw room type chart (guard empty)
        if room_labels and any(room_counts):
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.bar(room_labels, room_counts, color="#198754")
            ax2.set_title("🏨 Bookings per Room Type", fontsize=14, fontweight="bold", color="white")
            ax2.set_ylabel("Number of Bookings", color="white")
            ax2.set_xlabel("Room Type", color="white")
            apply_dark_style(ax2, fig2)
            plt.xticks(rotation=20, color="white")
            plt.yticks(color="white")
            key = f"chart_roomtype:{start_date}:{end_date}:{room_type or 'all'}"
            room_chart_base64 = cached_chart(key, lambda: fig_to_base64(fig2), timeout=300)

        else:
            room_chart_base64 = ""

        # --- Weekly line chart ---
        if labels and any(data):
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.plot(labels, data, marker="o", color="#0dcaf0", linewidth=2)
            ax.fill_between(labels, data, color="#0dcaf0", alpha=0.25)
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_title("📈 Weekly Bookings", fontsize=14, fontweight="bold", color="white")
            ax.set_ylabel("Bookings", color="white")
            ax.set_xlabel("Date", color="white")
            apply_dark_style(ax, fig)
            plt.xticks(rotation=30, color="white", fontsize=9)
            plt.yticks(color="white", fontsize=9)
            key = f"chart_weekly:{start_date}:{end_date}:{room_type or 'all'}"
            chart_base64 = cached_chart(key, lambda: fig_to_base64(fig), timeout=300)
        else:
            chart_base64 = ""

        # --- Revenue per Room Type ---
        revenue_per_type = bookings_qs.values("room__room_type").annotate(total_revenue=Sum("room__price")).order_by(
            "-total_revenue"
        )

        # --- Daily Revenue Trend ---
        revenue_data = bookings_qs.values("check_in").annotate(total=Sum("room__price")).order_by("check_in")
        revenue_labels = [r["check_in"].strftime("%b %d") for r in revenue_data if r.get("check_in")]
        revenue_totals = [r["total"] for r in revenue_data if r.get("check_in")]

        if revenue_labels and any(revenue_totals):
            fig4, ax4 = plt.subplots(figsize=(7, 4))
            ax4.plot(revenue_labels, revenue_totals, marker="o", color="#28a745", linewidth=2)
            ax4.fill_between(revenue_labels, revenue_totals, color="#28a745", alpha=0.25)
            ax4.set_title("💰 Revenue Trend (Daily)", fontsize=14, fontweight="bold", color="white")
            ax4.set_ylabel("Revenue ($)", color="white")
            apply_dark_style(ax4, fig4)
            plt.xticks(rotation=30, color="white")
            plt.yticks(color="white")
            ax4.grid(True, linestyle="--", alpha=0.4)
            key = f"chart_revenue:{start_date}:{end_date}:{room_type or 'all'}"
            revenue_chart_base64 = cached_chart(key, lambda: fig_to_base64(fig4), timeout=300)

        else:
            revenue_chart_base64 = ""

        # --- Average Stay Duration (in days) ---
        avg_stay = bookings_qs.annotate(
            stay_length=ExpressionWrapper(F("check_out") - F("check_in"), output_field=DurationField())
        ).aggregate(avg_days=Avg("stay_length"))
        avg_stay_days = (avg_stay["avg_days"].days if avg_stay["avg_days"] else 0)

        # --- Occupancy Rate ---
        booked_days = sum([(b.check_out - b.check_in).days for b in bookings_qs if b.check_out and b.check_in])
        days_span = (end_date - start_date).days + 1 if (end_date and start_date) else 30
        if days_span <= 0:
            days_span = 30
        total_room_days = Room.objects.count() * days_span
        occupancy_rate = round((booked_days / total_room_days) * 100, 2) if total_room_days else 0

        # --- Occupancy Pie Chart ---
        if total_room_days > 0:
            values_pie = [booked_days, max(total_room_days - booked_days, 0)]
            if sum(values_pie) > 0:
                fig3, ax3 = plt.subplots(figsize=(5, 5))
                labels_pie = ["Booked", "Available"]
                colors = ["#0d6efd", "#6c757d"]
                ax3.pie(values_pie, labels=labels_pie, autopct="%1.1f%%", startangle=140, colors=colors)
                fig3.patch.set_facecolor("#1e3c72")
                key = f"chart_occupancy:{start_date}:{end_date}:{room_type or 'all'}"
                occupancy_chart_base64 = cached_chart(key, lambda: fig_to_base64(fig3), timeout=300)

            else:
                occupancy_chart_base64 = ""
        else:
            occupancy_chart_base64 = ""

        # --- Bookings by Source ---
        source_data = bookings_qs.values("source").annotate(total=Count("id")).order_by("-total")
        source_labels = [s["source"] for s in source_data]
        source_counts = [s["total"] for s in source_data]

        if source_labels and any(source_counts):
            fig5, ax5 = plt.subplots(figsize=(6, 4))
            ax5.bar(source_labels, source_counts, color="#ffc107")
            ax5.set_title("📊 Bookings by Source", fontsize=14, fontweight="bold", color="white")
            ax5.set_ylabel("Number of Bookings", color="white")
            apply_dark_style(ax5, fig5)
            plt.xticks(rotation=15, color="white")
            plt.yticks(color="white")
            key = f"chart_source:{start_date}:{end_date}:{room_type or 'all'}"
            source_chart_base64 = cached_chart(key, lambda: fig_to_base64(fig5), timeout=300)

        else:
            source_chart_base64 = ""

        # ✅ CSV export
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=bookings.csv"
            writer = csv.writer(response)
            writer.writerow(["Customer", "Room", "Check-in", "Check-out", "Created At"])
            for b in bookings_qs:
                writer.writerow([b.customer_name, b.room.room_number, b.check_in, b.check_out, b.created_at])
            return response

        # ✅ PDF export
        if request.GET.get("export") == "pdf":
            html_string = render_to_string(
                "admin/pdf_report.html",
                {
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
                    "revenue_chart": revenue_chart_base64,
                    "source_chart": source_chart_base64,
                    "filter_start": start_date,
                    "filter_end": end_date,
                    "filter_room_type": room_type,
                },
            )
            pdf_file = HTML(string=html_string).write_pdf()
            response = HttpResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = "attachment; filename=bookings_report.pdf"
            return response

        # --- Top rooms: return Room instances (in order) with total_bookings attached ---
        top_rooms_counts = (
            bookings_qs.values("room")
            .annotate(total_bookings=Count("id"))
            .order_by("-total_bookings")[:3]
        )
        room_ids = [item["room"] for item in top_rooms_counts]
        rooms_qs = Room.objects.filter(id__in=room_ids)
        id_to_count = {item["room"]: item["total_bookings"] for item in top_rooms_counts}
        rooms_map = {r.id: r for r in rooms_qs}
        top_rooms = []
        for rid in room_ids:
            r = rooms_map.get(rid)
            if r:
                # attach attribute to the instance so template can read room.total_bookings
                r.total_bookings = id_to_count.get(rid, 0)
                top_rooms.append(r)

        recent_bookings = bookings_qs.order_by("-created_at")[:5]


        # --- Top rooms (as dicts with status) & recent bookings ---
        top_rooms_agg = (
            bookings_qs.values("room")
            .annotate(total_bookings=Count("id"))
            .order_by("-total_bookings")[:3]
        )
        room_ids = [a["room"] for a in top_rooms_agg]
        rooms = Room.objects.filter(id__in=room_ids)
        room_map = {r.id: r for r in rooms}
        top_rooms = []
        for a in top_rooms_agg:
            r = room_map.get(a["room"])
            top_rooms.append({
                "room_number": r.room_number if r else "",
                "room_type": r.room_type if r else "",
                "status": r.status if r else "",
                "total_bookings": a["total_bookings"],
            })

        recent_bookings = bookings_qs.order_by("-created_at")[:5]


        # --- Context for dashboard (single, clean dict — no duplicate keys) ---
        context = dict(
            self.each_context(request),
            today=today,
            total_rooms=total_rooms,
            total_bookings=total_bookings,
            today_checkins=today_checkins,
            today_checkouts=today_checkouts,
            # PNG fallbacks (for PDF export)
            chart=chart_base64,
            room_chart=room_chart_base64,
            occupancy_chart=occupancy_chart_base64,
            revenue_chart=revenue_chart_base64,
            source_chart=source_chart_base64,
            # SVG fallbacks for inline (non-JS interactive)
            chart_svg=locals().get("chart_svg", ""),
            room_chart_svg=locals().get("room_chart_svg", ""),
            # Data lists & KPIs
            top_rooms=top_rooms,
            recent_bookings=recent_bookings,
            revenue_per_type=revenue_per_type,
            avg_stay_days=avg_stay_days,
            occupancy_rate=occupancy_rate,
            # Filters to show in template if needed
            filter_start=start_date,
            filter_end=end_date,
            filter_room_type=room_type,
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
                '<img src="{}" width="60" height="40" style="object-fit:cover;" />', obj.image.url
            )
        return "No Image"

    preview_image.short_description = "Image"


# --- Booking Admin ---
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "room", "check_in", "check_out", "created_at", "user", "source")
    list_filter = ("check_in", "check_out", "room__room_type", "source")
    search_fields = ("customer_name", "room__room_number", "user__username", "user__email")
    ordering = ("-created_at",)
