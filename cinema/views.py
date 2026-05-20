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
import random
import string
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


@login_required
def seat_selection(request, showtime_id):
    showtime = get_object_or_404(
        Showtime.objects.select_related(
            "movie",
            "room",
            "room__cinema",
        ),
        id=showtime_id,
    )

    now = timezone.now()

    # booking pending quá hạn thì chuyển expired
    Booking.objects.filter(
        showtime=showtime, status="pending", hold_expires_at__lt=now
    ).update(status="expired")

    seats = showtime.room.seats.all().order_by("row", "number")


    locked_seat_ids = (
        BookingSeat.objects.filter(
            booking__showtime=showtime,
            booking__status__in=["pending", "paid"],
        )
        .filter(
            models.Q(booking__status="paid")
            | models.Q(booking__status="pending", booking__hold_expires_at__gt=now)
        )
        .values_list("seat_id", flat=True)
    )

    seat_rows_dict = {}

    for seat in seats:
        if seat.row not in seat_rows_dict:
            seat_rows_dict[seat.row] = []

        seat_rows_dict[seat.row].append(seat)

    seat_rows = []

    for row_label, row_seats in seat_rows_dict.items():
        seat_rows.append(
            {
                "row_label": row_label,
                "seats": row_seats,
            }
        )

    context = {
        "showtime": showtime,
        "seats": seats,
        "locked_seat_ids": list(locked_seat_ids),
    }

    return render(request, "cinema/seat_selection.html", context)


@login_required
def payment(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.prefetch_related("booking_seats__seat").select_related(
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
        ),
        id=booking_id,
        user=request.user,
    )

    if booking.status == "paid":
        return redirect("cinema:payment_success", booking_id=booking.id)

    if booking.status in ["cancelled", "expired"]:
        messages.error(request, "Booking này đã hết hạn hoặc đã bị hủy.")
        return redirect("cinema:seat_selection", showtime_id=booking.showtime.id)

    return render(request, "cinema/payment.html", {"booking": booking})


def generate_transaction_id():
    return "VNPAY" + "".join(random.choices(string.digits, k=10))


@login_required
def vnpay_payment(request, booking_id):
    if request.method != "POST":
        return redirect("cinema:payment", booking_id=booking_id)

    booking = get_object_or_404(
        Booking.objects.prefetch_related("booking_seats__seat").select_related(
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
        ),
        id=booking_id,
        user=request.user,
    )

    if booking.status == "paid":
        return redirect("cinema:payment_success", booking_id=booking.id)

    transaction_id = generate_transaction_id()

    Payment.objects.update_or_create(
        booking=booking,
        defaults={
            "method": "vnpay",
            "status": "pending",
            "amount": booking.total_price,
            "transaction_id": transaction_id,
        },
    )

    return render(
        request,
        "cinema/vnpay_mock.html",
        {
            "booking": booking,
            "transaction_id": transaction_id,
        },
    )


@login_required
def vnpay_return(request, booking_id):
    if request.method != "POST":
        return redirect("cinema:payment", booking_id=booking_id)

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user,
    )

    result = request.POST.get("result")
    transaction_id = request.POST.get("transaction_id")

    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            "method": "vnpay",
            "amount": booking.total_price,
        },
    )

    payment.method = "vnpay"
    payment.transaction_id = transaction_id
    payment.amount = booking.total_price

    if result == "success":
        payment.status = "paid"
        payment.paid_at = timezone.now()
        payment.save()

        booking.status = "paid"
        booking.save()

        ticket, created = Ticket.objects.get_or_create(
            booking=booking, defaults={"status": "valid"}
        )

        if created or not ticket.qr_code:
            generate_ticket_qr(ticket)

        return redirect("cinema:payment_success", booking_id=booking.id)

    payment.status = "failed"

    payment.save()

    booking.status = "cancelled"
    booking.save()

    return redirect("cinema:payment_failed", booking_id=booking.id)


@login_required
def payment_failed(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
        ),
        id=booking_id,
        user=request.user,
    )

    return render(request, "cinema/payment_failed.html", {"booking": booking})


@login_required
def confirm_payment(request, booking_id):
    if request.method != "POST":
        return redirect("cinema:payment", booking_id=booking_id)

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    booking.status = "paid"
    booking.save()

    Payment.objects.update_or_create(
        booking=booking,
        defaults={
            "method": "cash",
            "status": "paid",
            "amount": booking.total_price,
            "paid_at": timezone.now(),
        },
    )

    ticket, created = Ticket.objects.get_or_create(
        booking=booking, defaults={"status": "valid"}
    )

    if created or not ticket.qr_code:
        generate_ticket_qr(ticket)
        return redirect("cinema:payment_success", booking_id=booking.id)


@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.prefetch_related("booking_seats__seat"),
        id=booking_id,
        user=request.user,
    )

    return render(request, "cinema/payment_success.html", {"booking": booking})


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
def create_booking(request, showtime_id):
    if request.method != "POST":
        return redirect("cinema:seat_selection", showtime_id=showtime_id)

    showtime = get_object_or_404(
        Showtime.objects.select_related("room"), id=showtime_id
    )

    seat_ids_str = request.POST.get("seat_ids", "")

    if not seat_ids_str:
        messages.error(request, "Vui lòng chọn ít nhất một ghế.")
        return redirect("cinema:seat_selection", showtime_id=showtime_id)

    seat_ids = seat_ids_str.split(",")
    now = timezone.now()

    # Dọn booking pending đã hết hạn
    Booking.objects.filter(
        showtime=showtime, status="pending", hold_expires_at__lt=now
    ).update(status="expired")

    try:
        with transaction.atomic():
            seats = Seat.objects.select_for_update().filter(
                id__in=seat_ids, room=showtime.room
            )

            if seats.count() != len(seat_ids):
                messages.error(request, "Danh sách ghế không hợp lệ.")
                return redirect("cinema:seat_selection", showtime_id=showtime_id)

            # Check ghế đã bị paid hoặc đang pending chưa hết hạn
            locked_seat_ids = (
                BookingSeat.objects.filter(
                    seat_id__in=seat_ids,
                    booking__showtime=showtime,
                    booking__status__in=["pending", "paid"],
                )
                .exclude(booking__status="pending", booking__hold_expires_at__lt=now)
                .values_list("seat_id", flat=True)
            )

            if locked_seat_ids:
                messages.error(
                    request,
                    "Một số ghế vừa được người khác giữ. Vui lòng chọn ghế khác.",
                )
                return redirect("cinema:seat_selection", showtime_id=showtime_id)

            booking_code = "CF" + "".join(random.choices(string.digits, k=8))

            total_price = showtime.price * seats.count()

            booking = Booking.objects.create(
                user=request.user,
                showtime=showtime,
                booking_code=booking_code,
                total_price=total_price,
                status="pending",
                hold_expires_at=now + timedelta(minutes=5),
            )

            for seat in seats:
                BookingSeat.objects.create(
                    booking=booking, seat=seat, price=showtime.price
                )

    except Exception as e:
        messages.error(request, "Có lỗi xảy ra khi tạo booking. Vui lòng thử lại.")
        return redirect("cinema:seat_selection", showtime_id=showtime_id)

    return redirect("cinema:payment", booking_id=booking.id)


@login_required
def booking_detail(request, booking_id):

    booking = get_object_or_404(
        Booking.objects.prefetch_related("booking_seats__seat"),
        id=booking_id,
        user=request.user,
    )

    return render(request, "cinema/booking_detail.html", {"booking": booking})


def generate_ticket_qr(ticket):

    booking = ticket.booking

    seats = ", ".join(
        [f"{item.seat.row}{item.seat.number}" for item in booking.booking_seats.all()]
    )

    qr_data = (
        f"CINEFLOW E-TICKET\n"
        f"====================\n"
        f"Booking Code: {booking.booking_code}\n"
        f"Movie: {booking.showtime.movie.title}\n"
        f"Cinema: {booking.showtime.room.cinema.name}\n"
        f"Room: {booking.showtime.room.name}\n"
        f"Seats: {seats}\n"
        f"Showtime: {booking.showtime.start_time.strftime('%d/%m/%Y %H:%M')}\n"
        f"Total: {booking.total_price} VND\n"
        f"Status: {booking.status.upper()}\n"
        f"====================\n"
        f"Please present this QR code at the cinema."
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    buffer = BytesIO()

    img.save(buffer, format="PNG")

    file_name = f"ticket_{booking.booking_code}.png"

    ticket.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)

    qr_data = "HELLO CINEFLOW"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()

    img.save(buffer, format="PNG")

    file_name = f"ticket_{ticket.booking.booking_code}.png"

    ticket.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
    qr_data = f"https://cineflow.local/ticket/{ticket.booking.booking_code}"

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=8,
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    file_name = f"ticket_{ticket.booking.booking_code}.png"

    ticket.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)

    print("QR DATA:", qr_data)
    seats = ", ".join(
        [
            f"{item.seat.row}{item.seat.number}"
            for item in ticket.booking.booking_seats.all()
        ]
    )

    qr_data = (
        f"BOOKING_CODE: {ticket.booking.booking_code}\n"
        f"MOVIE: {ticket.booking.showtime.movie.title}\n"
        f"CINEMA: {ticket.booking.showtime.room.cinema.name}\n"
        f"ROOM: {ticket.booking.showtime.room.name}\n"
        f"SEATS: {seats}\n"
        f"TIME: {ticket.booking.showtime.start_time.strftime('%d/%m/%Y %H:%M')}\n"
        f"STATUS: {ticket.booking.status}"
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    file_name = f"ticket_{ticket.booking.booking_code}.png"

    ticket.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
    seats = ", ".join(
        [
            f"{item.seat.row}{item.seat.number}"
            for item in ticket.booking.booking_seats.all()
        ]
    )

    qr_data = f"""
    BOOKING:{ticket.booking.booking_code}
    MOVIE:{ticket.booking.showtime.movie.title}
    CINEMA:{ticket.booking.showtime.room.cinema.name}
    ROOM:{ticket.booking.showtime.room.name}
    SEATS:{seats}
    TIME:{ticket.booking.showtime.start_time}
    """

    img = qrcode.make(qr_data)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    file_name = f"ticket_{ticket.booking.booking_code}.png"

    ticket.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)

    qr_data = f"http://127.0.0.1:8000/ticket/{ticket.booking.booking_code}/"

    print(qr_data)





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



    