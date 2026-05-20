from django.shortcuts import render, get_object_or_404
from .models import *
import random
import string
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone
from django.core.files.base import ContentFile
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth import login, logout
from .forms import RegisterForm, LoginForm
from .forms import RegisterForm

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from datetime import timedelta
from django.db import transaction
from django.contrib import messages
from django.db import models
from django.utils import timezone
from collections import OrderedDict
from django.db.models import Sum, Count
from .app_views.manage_views import *
from .app_views.staff_views import *
from .app_views.ticket_views import *
from .app_views.booking_views import *
from .app_views.payment_views import *


def home(request):
    now_showing_movies = Movie.objects.filter(status="now_showing").order_by(
        "-created_at"
    )[:8]
    coming_soon_movies = Movie.objects.filter(status="coming_soon").order_by(
        "-created_at"
    )[:5]

    context = {
        "now_showing_movies": now_showing_movies,
        "coming_soon_movies": coming_soon_movies,
    }

    return render(request, "cinema/home.html", context)


def movie_list(request):
    search_query = request.GET.get("q", "")
    cinema_id = request.GET.get("cinema", "")
    genre = request.GET.get("genre", "")
    status = request.GET.get("status", "")

    cinemas = Cinema.objects.all().order_by("name")

    movies = Movie.objects.all().order_by("title")

    if search_query:
        movies = movies.filter(title__icontains=search_query)

    if genre:
        movies = movies.filter(genre__icontains=genre)

    if status:
        movies = movies.filter(status=status)

    if cinema_id:
        movies = movies.filter(
            showtimes__room__cinema_id=cinema_id
        ).distinct()

    genres = Movie.objects.exclude(
        genre__isnull=True
    ).exclude(
        genre=""
    ).values_list(
        "genre",
        flat=True
    ).distinct()

    now_showing_movies = movies.filter(status="now_showing")
    coming_soon_movies = movies.filter(status="coming_soon")

    context = {
        "cinemas": cinemas,
        "genres": genres,
        "selected_cinema_id": cinema_id,
        "selected_genre": genre,
        "selected_status": status,
        "search_query": search_query,
        "now_showing_movies": now_showing_movies,
        "coming_soon_movies": coming_soon_movies,
    }

    return render(request, "cinema/movie_list.html", context)


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    showtimes = Showtime.objects.none()

    if movie.status == "now_showing":
        showtimes = (
            Showtime.objects.filter(movie=movie, start_time__gte=timezone.now())
            .select_related(
                "room",
                "room__cinema",
            )
            .order_by("start_time")
        )

    context = {
        "movie": movie,
        "showtimes": showtimes,
    }

    return render(request, "cinema/movie_detail.html", context)


def cinema_list(request):
    cinemas = Cinema.objects.prefetch_related("rooms").all()

    return render(request, "cinema/cinema_list.html", {"cinemas": cinemas})


def showtime_list(request):
    selected_date = request.GET.get("date", "")
    cinema_id = request.GET.get("cinema", "")

    showtimes = Showtime.objects.filter(
        movie__status="now_showing",
        start_time__gte=timezone.now()
    ).select_related(
        "movie",
        "room",
        "room__cinema"
    ).order_by(
        "start_time",
        "movie__title",
        "room__cinema__name"
    )

    if selected_date:
        showtimes = showtimes.filter(
            start_time__date=selected_date
        )

    if cinema_id:
        showtimes = showtimes.filter(
            room__cinema_id=cinema_id
        )

    cinemas = Cinema.objects.all().order_by("name")

    context = {
        "showtimes": showtimes,
        "cinemas": cinemas,
        "selected_date": selected_date,
        "selected_cinema_id": cinema_id,
    }

    return render(request, "cinema/showtime_list.html", context)



def profile(request):
    return render(request, "cinema/profile.html")


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    now = timezone.localtime()
    today = now.date()

    total_revenue = Booking.objects.filter(
        status="paid"
    ).aggregate(
        total=Sum("total_price")
    )["total"] or 0

    today_revenue = Booking.objects.filter(
        status="paid",
        created_at__date=today
    ).aggregate(
        total=Sum("total_price")
    )["total"] or 0

    month_revenue = Booking.objects.filter(
        status="paid",
        created_at__year=today.year,
        created_at__month=today.month
    ).aggregate(
        total=Sum("total_price")
    )["total"] or 0

    paid_bookings = Booking.objects.filter(status="paid").count()
    checked_in_tickets = Ticket.objects.filter(status="used").count()
    total_showtimes = Showtime.objects.count()

    # Revenue 7 ngày gần nhất
    revenue_days = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        amount = Booking.objects.filter(
            status="paid",
            created_at__date=day
        ).aggregate(
            total=Sum("total_price")
        )["total"] or 0

        revenue_days.append({
            "label": day.strftime("%d/%m"),
            "amount": amount,
        })

    max_revenue = max([item["amount"] for item in revenue_days], default=0)

    for item in revenue_days:
        if max_revenue > 0:
            item["percent"] = int((item["amount"] / max_revenue) * 100)
        else:
            item["percent"] = 8

        if item["percent"] < 8:
            item["percent"] = 8

    recent_paid_bookings = Booking.objects.filter(
        status="paid"
    ).select_related(
        "user",
        "showtime",
        "showtime__movie",
        "showtime__room",
        "showtime__room__cinema",
    ).prefetch_related(
        "booking_seats__seat"
    ).order_by("-created_at")[:8]

    top_movies = Booking.objects.filter(
        status="paid"
    ).values(
        "showtime__movie__title"
    ).annotate(
        revenue=Sum("total_price"),
        tickets_sold=Count("booking_seats")
    ).order_by("-revenue")[:5]

    max_movie_revenue = max(
        [item["revenue"] or 0 for item in top_movies],
        default=0
    )

    for item in top_movies:
        if max_movie_revenue > 0:
            item["percent"] = int((item["revenue"] / max_movie_revenue) * 100)
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
        Booking.objects.prefetch_related("booking_seats__seat"),
        id=booking_id,
        user=request.user,
    )

    return render(request, "cinema/booking_detail.html", {"booking": booking})


@login_required
def check_in_ticket(request, booking_code):

    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền thực hiện thao tác này.")

        return redirect("cinema:ticket_detail", booking_code=booking_code)

    if request.method != "POST":
        return redirect("cinema:ticket_detail", booking_code=booking_code)

    booking = get_object_or_404(
        Booking.objects.select_related("ticket"),
        booking_code=booking_code,
        status="paid",
    )

    ticket = booking.ticket

    if ticket.status == "used":
        messages.warning(request, "Vé này đã được sử dụng trước đó.")

    elif ticket.status == "cancelled":
        messages.error(request, "Vé này đã bị hủy.")

    else:
        ticket.status = "used"
        ticket.save()

        messages.success(request, "Check-in thành công.")

    return redirect("cinema:ticket_detail", booking_code=booking_code)


def register_view(request):

    if request.user.is_authenticated:
        return redirect("cinema:home")

    form = RegisterForm()

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            return redirect("cinema:home")

    return render(request, "cinema/register.html", {"form": form})


def login_view(request):

    if request.user.is_authenticated:
        return redirect("cinema:home")

    form = LoginForm()

    if request.method == "POST":

        form = LoginForm(request, data=request.POST)

        if form.is_valid():

            user = form.get_user()

            login(request, user)

            return redirect("cinema:home")

    return render(request, "cinema/login.html", {"form": form})


@login_required
def logout_view(request):

    logout(request)

    return redirect("cinema:home")



    