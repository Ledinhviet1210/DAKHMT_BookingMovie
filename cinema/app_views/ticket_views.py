from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from cinema.models import Booking
from django.utils import timezone

@login_required
def my_tickets(request):

    bookings = (
        Booking.objects.filter(user=request.user, status="paid")
        .select_related(
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
        )
        .prefetch_related("booking_seats__seat")
        .order_by("-created_at")
    )

    now = timezone.now()

    for booking in bookings:

        if booking.showtime.start_time > now:
            booking.ticket_status = "upcoming"

        else:
            booking.ticket_status = "watched"

    return render(request, "cinema/my_tickets.html", {"bookings": bookings})


def ticket_detail(request, booking_code):
    booking = get_object_or_404(
        Booking.objects.prefetch_related("booking_seats__seat").select_related(
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
        ),
        booking_code=booking_code,
        status="paid",
    )

    return render(request, "cinema/ticket_detail.html", {"booking": booking})