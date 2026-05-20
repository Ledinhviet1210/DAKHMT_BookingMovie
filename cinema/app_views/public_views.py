from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from cinema.models import (
    Movie,
    Cinema,
    Showtime,
)

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