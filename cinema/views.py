from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import RegisterForm, LoginForm
from .models import Booking, Ticket, Showtime

from .app_views.manage_views import *
from .app_views.staff_views import *
from .app_views.ticket_views import *
from .app_views.booking_views import *
from .app_views.payment_views import *
from .app_views.public_views import *
from .app_views.auth_views import *


def profile(request):
    return render(request, "cinema/profile.html")


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    now = timezone.localtime()
    today = now.date()

    total_revenue = (
        Booking.objects
        .filter(status="paid")
        .aggregate(total=Sum("total_price"))
        ["total"]
        or 0
    )

    today_revenue = (
        Booking.objects
        .filter(
            status="paid",
            created_at__date=today,
        )
        .aggregate(total=Sum("total_price"))
        ["total"]
        or 0
    )

    month_revenue = (
        Booking.objects
        .filter(
            status="paid",
            created_at__year=today.year,
            created_at__month=today.month,
        )
        .aggregate(total=Sum("total_price"))
        ["total"]
        or 0
    )

    paid_bookings = Booking.objects.filter(status="paid").count()

    checked_in_tickets = Ticket.objects.filter(
        status="used"
    ).count()

    total_showtimes = Showtime.objects.count()

    revenue_days = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        amount = (
            Booking.objects
            .filter(
                status="paid",
                created_at__date=day,
            )
            .aggregate(total=Sum("total_price"))
            ["total"]
            or 0
        )

        revenue_days.append({
            "label": day.strftime("%d/%m"),
            "amount": amount,
        })

    max_revenue = max(
        [item["amount"] for item in revenue_days],
        default=0,
    )

    for item in revenue_days:
        if max_revenue > 0:
            item["percent"] = int(
                (item["amount"] / max_revenue) * 100
            )
        else:
            item["percent"] = 8

        if item["percent"] < 8:
            item["percent"] = 8

    recent_paid_bookings = (
        Booking.objects
        .filter(status="paid")
        .select_related(
            "user",
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
        )
        .prefetch_related(
            "booking_seats__seat"
        )
        .order_by("-created_at")[:8]
    )

    top_movies = (
        Booking.objects
        .filter(status="paid")
        .values("showtime__movie__title")
        .annotate(
            revenue=Sum("total_price"),
            tickets_sold=Count("booking_seats"),
        )
        .order_by("-revenue")[:5]
    )

    max_movie_revenue = max(
        [item["revenue"] or 0 for item in top_movies],
        default=0,
    )

    for item in top_movies:
        if max_movie_revenue > 0:
            item["percent"] = int(
                (item["revenue"] / max_movie_revenue) * 100
            )
        else:
            item["percent"] = 0

    context = {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "paid_bookings": paid_bookings,
        "checked_in_tickets": checked_in_tickets,
        "total_showtimes": total_showtimes,
        "revenue_days": revenue_days,
        "recent_paid_bookings": recent_paid_bookings,
        "top_movies": top_movies,
    }

    return render(request, "cinema/admin_dashboard.html", context)


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.prefetch_related(
            "booking_seats__seat"
        ),
        id=booking_id,
        user=request.user,
    )

    return render(
        request,
        "cinema/booking_detail.html",
        {
            "booking": booking,
        }
    )


@login_required
def check_in_ticket(request, booking_code):
    if not request.user.is_staff:
        messages.error(
            request,
            "Bạn không có quyền thực hiện thao tác này."
        )

        return redirect(
            "cinema:ticket_detail",
            booking_code=booking_code,
        )

    if request.method != "POST":
        return redirect(
            "cinema:ticket_detail",
            booking_code=booking_code,
        )

    booking = get_object_or_404(
        Booking.objects.select_related("ticket"),
        booking_code=booking_code,
        status="paid",
    )

    ticket = booking.ticket

    if ticket.status == "used":
        messages.warning(
            request,
            "Vé này đã được sử dụng trước đó."
        )

    elif ticket.status == "cancelled":
        messages.error(
            request,
            "Vé này đã bị hủy."
        )

    else:
        ticket.status = "used"
        ticket.save()

        messages.success(
            request,
            "Check-in thành công."
        )

    return redirect(
        "cinema:ticket_detail",
        booking_code=booking_code,
    )


