from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from cinema.models import (
    Movie,
    Cinema,
    Room,
    Showtime,
    Booking,
    Payment,
    Ticket,
)


@login_required
def manage_movies(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    search_query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    genre = request.GET.get("genre", "")

    movies = Movie.objects.all().order_by("-created_at")

    if search_query:
        movies = movies.filter(title__icontains=search_query)

    if status:
        movies = movies.filter(status=status)

    if genre:
        movies = movies.filter(genre__icontains=genre)

    genres = (
        Movie.objects
        .exclude(genre__isnull=True)
        .exclude(genre="")
        .values_list("genre", flat=True)
        .distinct()
    )

    context = {
        "active_menu": "movies",
        "movies": movies,
        "genres": genres,
        "search_query": search_query,
        "selected_status": status,
        "selected_genre": genre,
    }

    return render(request, "cinema/manage/movie_manage.html", context)
    
    
@login_required
def manage_home(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    return redirect("cinema:manage_movies")


@login_required
def manage_showtimes(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    movie_id = request.GET.get("movie", "")
    cinema_id = request.GET.get("cinema", "")
    selected_date = request.GET.get("date", "")

    showtimes = Showtime.objects.select_related(
        "movie",
        "room",
        "room__cinema",
    ).order_by("-start_time")

    if movie_id:
        showtimes = showtimes.filter(movie_id=movie_id)

    if cinema_id:
        showtimes = showtimes.filter(room__cinema_id=cinema_id)

    if selected_date:
        showtimes = showtimes.filter(start_time__date=selected_date)

    movies = Movie.objects.all().order_by("title")
    cinemas = Cinema.objects.all().order_by("name")

    return render(
        request,
        "cinema/manage/showtime_manage.html",
        {
            "active_menu": "showtimes",
            "showtimes": showtimes,
            "movies": movies,
            "cinemas": cinemas,
            "selected_movie_id": movie_id,
            "selected_cinema_id": cinema_id,
            "selected_date": selected_date,
        }
    )


@login_required
def manage_bookings(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    status = request.GET.get("status", "")
    search_query = request.GET.get("q", "")

    bookings = Booking.objects.select_related(
        "user",
        "showtime",
        "showtime__movie",
        "showtime__room",
        "showtime__room__cinema",
    ).prefetch_related(
        "booking_seats__seat"
    ).order_by("-created_at")

    if status:
        bookings = bookings.filter(status=status)

    if search_query:
        bookings = bookings.filter(booking_code__icontains=search_query)

    return render(
        request,
        "cinema/manage/booking_manage.html",
        {
            "active_menu": "bookings",
            "bookings": bookings,
            "selected_status": status,
            "search_query": search_query,
        }
    )


@login_required
def manage_payments(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    status = request.GET.get("status", "")
    method = request.GET.get("method", "")
    search_query = request.GET.get("q", "")

    payments = Payment.objects.select_related(
        "booking",
        "booking__user",
        "booking__showtime",
        "booking__showtime__movie",
    ).order_by("-paid_at", "-id")

    if status:
        payments = payments.filter(status=status)

    if method:
        payments = payments.filter(method=method)

    if search_query:
        payments = payments.filter(booking__booking_code__icontains=search_query)

    return render(
        request,
        "cinema/manage/payment_manage.html",
        {
            "active_menu": "payments",
            "payments": payments,
            "selected_status": status,
            "selected_method": method,
            "search_query": search_query,
        }
    )


@login_required
def manage_tickets(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    status = request.GET.get("status", "")
    search_query = request.GET.get("q", "")

    tickets = Ticket.objects.select_related(
        "booking",
        "booking__user",
        "booking__showtime",
        "booking__showtime__movie",
        "booking__showtime__room",
        "booking__showtime__room__cinema",
    ).order_by("-issued_at")

    if status:
        tickets = tickets.filter(status=status)

    if search_query:
        tickets = tickets.filter(booking__booking_code__icontains=search_query)

    return render(
        request,
        "cinema/manage/ticket_manage.html",
        {
            "active_menu": "tickets",
            "tickets": tickets,
            "selected_status": status,
            "search_query": search_query,
        }
    )
    
    

@login_required
def manage_cinemas(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    search_query = request.GET.get("q", "")
    city = request.GET.get("city", "")

    cinemas = Cinema.objects.prefetch_related("rooms").all().order_by("name")

    if search_query:
        cinemas = cinemas.filter(name__icontains=search_query)

    if city:
        cinemas = cinemas.filter(city__icontains=city)

    cities = (
        Cinema.objects
        .exclude(city__isnull=True)
        .exclude(city="")
        .values_list("city", flat=True)
        .distinct()
    )

    return render(
        request,
        "cinema/manage/cinema_manage.html",
        {
            "active_menu": "cinemas",
            "cinemas": cinemas,
            "cities": cities,
            "search_query": search_query,
            "selected_city": city,
        }
    )


@login_required
def manage_rooms(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
        return redirect("cinema:home")

    cinema_id = request.GET.get("cinema", "")
    room_type = request.GET.get("room_type", "")

    rooms = Room.objects.select_related(
        "cinema"
    ).prefetch_related(
        "seats"
    ).all().order_by(
        "cinema__name",
        "name"
    )

    if cinema_id:
        rooms = rooms.filter(cinema_id=cinema_id)

    if room_type:
        rooms = rooms.filter(room_type=room_type)

    cinemas = Cinema.objects.all().order_by("name")

    return render(
        request,
        "cinema/manage/room_manage.html",
        {
            "active_menu": "rooms",
            "rooms": rooms,
            "cinemas": cinemas,
            "selected_cinema_id": cinema_id,
            "selected_room_type": room_type,
        }
    )