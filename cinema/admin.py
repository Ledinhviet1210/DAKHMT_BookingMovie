from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    Movie,
    Cinema,
    Room,
    Seat,
    Showtime,
    Booking,
    BookingSeat,
    Payment,
    Ticket,
)


# =========================
# Movie Admin
# =========================

class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    can_delete = False

    fields = (
        "row",
        "number",
    )

    readonly_fields = (
        "row",
        "number",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "cinema",
        "room_type",
        "total_rows",
        "seats_per_row",
        "seat_count",
    )

    list_filter = (
        "cinema",
        "room_type",
    )

    search_fields = (
        "name",
        "cinema__name",
    )

    inlines = [
        SeatInline,
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.seats.exists():
            return (
                "total_rows",
                "seats_per_row",
            )

        return ()

    def seat_count(self, obj):
        return obj.seats.count()

    seat_count.short_description = "Số ghế"


# =========================
# Cinema / Room / Seat Admin
# =========================

class RoomInline(admin.TabularInline):
    model = Room
    extra = 0
    fields = (
        "name",
        "room_type",
        "total_rows",
        "seats_per_row",
    )


@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "address",
        "room_count",
    )

    search_fields = (
        "name",
        "city",
        "address",
    )

    list_filter = (
        "city",
    )

    inlines = [
        RoomInline,
    ]

    def room_count(self, obj):
        return obj.rooms.count()

    room_count.short_description = "Số phòng"



# @admin.register(Seat)
# class SeatAdmin(admin.ModelAdmin):
#     list_display = (
#         "seat_name",
#         "room",
#         "cinema_name",
#     )

#     list_filter = (
#         "room__cinema",
#         "room",
#     )

#     search_fields = (
#         "row",
#         "number",
#         "room__name",
#         "room__cinema__name",
#     )

#     ordering = (
#         "room",
#         "row",
#         "number",
#     )

#     readonly_fields = (
#         "room",
#         "row",
#         "number",
#     )

#     def seat_name(self, obj):
#         return f"{obj.row}{obj.number}"

#     seat_name.short_description = "Ghế"

#     def cinema_name(self, obj):
#         return obj.room.cinema.name

#     cinema_name.short_description = "Rạp"

#     def has_add_permission(self, request):
#         return False

#     def has_change_permission(self, request, obj=None):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False


# =========================
# Showtime Admin
# =========================

@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = (
        "movie",
        "cinema_name",
        "room",
        "start_time",
        "end_time_display",
        "price",
    )

    list_filter = (
        "room__cinema",
        "room",
        "movie",
        "start_time",
    )

    search_fields = (
        "movie__title",
        "room__name",
        "room__cinema__name",
    )

    ordering = (
        "-start_time",
    )

    def cinema_name(self, obj):
        return obj.room.cinema.name

    cinema_name.short_description = "Rạp"

    def end_time_display(self, obj):
        try:
            return obj.get_end_time()
        except Exception:
            return "-"

    end_time_display.short_description = "Kết thúc"


# =========================
# Booking Admin
# =========================

class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    readonly_fields = (
        "seat",
        "price",
    )

    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_code",
        "user",
        "movie_title",
        "cinema_name",
        "room_name",
        "seat_list",
        "status_badge",
        "total_price",
        "hold_expires_at",
        "created_at",
    )

    list_filter = (
        "status",
        "showtime__room__cinema",
        "showtime__movie",
        "created_at",
    )

    search_fields = (
        "booking_code",
        "user__username",
        "user__email",
        "showtime__movie__title",
    )

    readonly_fields = (
        "booking_code",
        "user",
        "showtime",
        "status",
        "total_price",
        "hold_expires_at",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    inlines = [
        BookingSeatInline,
    ]

    def movie_title(self, obj):
        return obj.showtime.movie.title

    movie_title.short_description = "Phim"

    def cinema_name(self, obj):
        return obj.showtime.room.cinema.name

    cinema_name.short_description = "Rạp"

    def room_name(self, obj):
        return obj.showtime.room.name

    room_name.short_description = "Phòng"

    def seat_list(self, obj):
        seats = [
            f"{item.seat.row}{item.seat.number}"
            for item in obj.booking_seats.all()
        ]

        return ", ".join(seats)

    seat_list.short_description = "Ghế"

    def status_badge(self, obj):
        if obj.status == "paid":
            return format_html(
                '<span style="background:#dcfce7;color:#166534;padding:4px 10px;border-radius:999px;font-weight:700;">Đã thanh toán</span>'
            )

        if obj.status == "pending":
            return format_html(
                '<span style="background:#fef9c3;color:#854d0e;padding:4px 10px;border-radius:999px;font-weight:700;">Đang giữ ghế</span>'
            )

        if obj.status == "cancelled":
            return format_html(
                '<span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:999px;font-weight:700;">Đã hủy</span>'
            )

        if obj.status == "expired":
            return format_html(
                '<span style="background:#e5e7eb;color:#374151;padding:4px 10px;border-radius:999px;font-weight:700;">Hết hạn</span>'
            )

        return obj.status

    status_badge.short_description = "Trạng thái"


# =========================
# Payment Admin
# =========================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "booking_code",
        "method",
        "status_badge",
        "transaction_id",
        "amount",
        "paid_at",
    )

    list_filter = (
        "method",
        "status",
        "paid_at",
    )

    search_fields = (
        "booking__booking_code",
        "transaction_id",
        "booking__user__username",
    )

    readonly_fields = (
        "booking",
        "method",
        "status",
        "transaction_id",
        "amount",
        "paid_at",
    )

    def booking_code(self, obj):
        return obj.booking.booking_code

    booking_code.short_description = "Mã booking"

    def status_badge(self, obj):
        if obj.status == "paid":
            return format_html(
                '<span style="background:#dcfce7;color:#166534;padding:4px 10px;border-radius:999px;font-weight:700;">Paid</span>'
            )

        if obj.status == "pending":
            return format_html(
                '<span style="background:#fef9c3;color:#854d0e;padding:4px 10px;border-radius:999px;font-weight:700;">Pending</span>'
            )

        if obj.status == "failed":
            return format_html(
                '<span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:999px;font-weight:700;">Failed</span>'
            )

        return obj.status

    status_badge.short_description = "Trạng thái"


# =========================
# Ticket Admin
# =========================

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "booking_code",
        "user",
        "movie_title",
        "status_badge",
        "issued_at",
    )

    list_filter = (
        "status",
        "issued_at",
    )

    search_fields = (
        "booking__booking_code",
        "booking__user__username",
        "booking__showtime__movie__title",
    )

    readonly_fields = (
        "booking",
        "qr_code",
        "status",
        "issued_at",
    )

    def booking_code(self, obj):
        return obj.booking.booking_code

    booking_code.short_description = "Mã booking"

    def user(self, obj):
        return obj.booking.user.username

    user.short_description = "Khách hàng"

    def movie_title(self, obj):
        return obj.booking.showtime.movie.title

    movie_title.short_description = "Phim"

    def status_badge(self, obj):
        if obj.status == "valid":
            return format_html(
                '<span style="background:#dcfce7;color:#166534;padding:4px 10px;border-radius:999px;font-weight:700;">Valid</span>'
            )

        if obj.status == "used":
            return format_html(
                '<span style="background:#e5e7eb;color:#374151;padding:4px 10px;border-radius:999px;font-weight:700;">Used</span>'
            )

        if obj.status == "cancelled":
            return format_html(
                '<span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:999px;font-weight:700;">Cancelled</span>'
            )

        return obj.status

    status_badge.short_description = "Trạng thái"