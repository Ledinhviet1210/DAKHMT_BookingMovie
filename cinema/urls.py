from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "cinema"

urlpatterns = [
    path("", views.home, name="home"),
    path("manage/", views.manage_home, name="manage_home"),
    path("manage/movies/", views.manage_movies, name="manage_movies"),
    path("manage/cinemas/", views.manage_cinemas, name="manage_cinemas"),
    path("manage/rooms/", views.manage_rooms, name="manage_rooms"),
    path("manage/showtimes/", views.manage_showtimes, name="manage_showtimes"),
    path("manage/bookings/", views.manage_bookings, name="manage_bookings"),
    path("manage/payments/", views.manage_payments, name="manage_payments"),
    path("manage/tickets/", views.manage_tickets, name="manage_tickets"),
    path("movies/", views.movie_list, name="movie_list"),
    path("movies/<int:movie_id>/", views.movie_detail, name="movie_detail"),
    path("showtimes/", views.showtime_list, name="showtime_list"),
    path("cinemas/", views.cinema_list, name="cinema_list"),
    path(
        "seat-selection/<int:showtime_id>/", views.seat_selection, name="seat_selection"
    ),
    path(
        "payment-success/<int:booking_id>/",
        views.payment_success,
        name="payment_success",
    ),
    path("my-tickets/", views.my_tickets, name="my_tickets"),
    path("profile/", views.profile, name="profile"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "create-booking/<int:showtime_id>/",
        views.create_booking,
        name="create_booking",
    ),
    path(
        "booking/<int:booking_id>/",
        views.booking_detail,
        name="booking_detail",
    ),
    path("payment/<int:booking_id>/", views.payment, name="payment"),
    path(
        "confirm-payment/<int:booking_id>/",
        views.confirm_payment,
        name="confirm_payment",
    ),
    path(
        "ticket/<str:booking_code>/",
        views.ticket_detail,
        name="ticket_detail",
    ),
    path(
        "ticket/<str:booking_code>/check-in/",
        views.check_in_ticket,
        name="check_in_ticket",
    ),
    path(
        "payment/<int:booking_id>/vnpay/",
        views.vnpay_payment,
        name="vnpay_payment",
    ),
    path(
        "payment/<int:booking_id>/vnpay/return/",
        views.vnpay_return,
        name="vnpay_return",
    ),
    path(
        "payment-failed/<int:booking_id>/",
        views.payment_failed,
        name="payment_failed",
    ),
    path(
        "staff/check-in/",
        views.staff_checkin,
        name="staff_checkin",
    ),
    path(
        "staff/check-in/<str:booking_code>/confirm/",
        views.staff_confirm_checkin,
        name="staff_confirm_checkin",
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
