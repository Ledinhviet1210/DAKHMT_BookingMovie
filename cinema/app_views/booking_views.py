import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import random
import string
from cinema.models import (
    Showtime,
    Seat,
    Booking,
    BookingSeat,
)

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