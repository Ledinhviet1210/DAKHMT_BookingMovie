import uuid
import qrcode
from io import BytesIO
import string
import random
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from cinema.models import (
    Booking,
    Payment,
    Ticket,
)


def generate_transaction_id():
    return "VNPAY" + "".join(random.choices(string.digits, k=10))


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