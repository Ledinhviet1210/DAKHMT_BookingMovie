from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from cinema.models import Booking

@login_required
def staff_checkin(request):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang check-in.")
        return redirect("cinema:home")

    booking = None
    booking_code = request.GET.get("booking_code", "").strip()

    if booking_code:
        booking = Booking.objects.filter(
            booking_code__iexact=booking_code,
            status="paid",
        ).select_related(
            "user",
            "showtime",
            "showtime__movie",
            "showtime__room",
            "showtime__room__cinema",
            "ticket",
        ).prefetch_related(
            "booking_seats__seat"
        ).first()

        if not booking:
            messages.error(
                request,
                "Không tìm thấy vé hợp lệ với mã booking này."
            )

    return render(
        request,
        "cinema/staff_checkin.html",
        {
            "booking": booking,
            "booking_code": booking_code,
        }
    )


@login_required
def staff_confirm_checkin(request, booking_code):
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền check-in vé.")
        return redirect("cinema:home")

    if request.method != "POST":
        return redirect("cinema:staff_checkin")

    booking = get_object_or_404(
        Booking.objects.select_related("ticket"),
        booking_code__iexact=booking_code,
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
        messages.success(request, "Check-in thành công. Vé đã được đánh dấu là đã sử dụng.")

    return redirect(
        "cinema:staff_checkin"
    )