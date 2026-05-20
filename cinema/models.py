from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models

class Movie(models.Model):
    STATUS_CHOICES = (
        ("now_showing", "Now Showing"),
        ("coming_soon", "Coming Soon"),
        ("ended", "Ended"),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    genre = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    age_rating = models.CharField(max_length=20, default="PG-13")
    director = models.CharField(max_length=255, blank=True)
    actors = models.TextField(blank=True)
    poster = models.ImageField(upload_to="posters/", blank=True, null=True)
    trailer_url = models.URLField(blank=True)
    release_date = models.DateField(blank=True, null=True)
    rating = models.FloatField(default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="now_showing"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Cinema(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100, default="Ha Noi")
    image = models.ImageField(upload_to="cinemas/", blank=True, null=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    ROOM_TYPE_CHOICES = (
        ("standard", "Standard"),
        ("imax", "IMAX"),
        ("vip", "VIP"),
    )

    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=100)
    room_type = models.CharField(
        max_length=50, choices=ROOM_TYPE_CHOICES, default="standard"
    )
    total_rows = models.PositiveIntegerField(default=10)
    seats_per_row = models.PositiveIntegerField(default=14)

    def __str__(self):
        return f"{self.cinema.name} - {self.name}"

    def generate_seats(self):
        if self.seats.exists():
            return

        for row_index in range(self.total_rows):
            row_letter = chr(65 + row_index)

            for seat_number in range(1, self.seats_per_row + 1):
                Seat.objects.create(room=self, row=row_letter, number=seat_number)


class Seat(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="seats")
    row = models.CharField(max_length=5)
    number = models.PositiveIntegerField()

    class Meta:
        unique_together = ("room", "row", "number")
        ordering = ["row", "number"]

    def __str__(self):
        return f"{self.row}{self.number}"


class Showtime(models.Model):
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name="showtimes"
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="showtimes"
    )

    start_time = models.DateTimeField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def get_end_time(self):
        return self.start_time + timedelta(minutes=self.movie.duration)

    def clean(self):
        super().clean()

        if not self.movie or not self.room or not self.start_time:
            return

        current_start = self.start_time
        current_end = self.get_end_time()

        showtimes = Showtime.objects.filter(
            room=self.room
        ).exclude(
            id=self.id
        )

        for showtime in showtimes:
            existing_start = showtime.start_time
            existing_end = showtime.start_time + timedelta(
                minutes=showtime.movie.duration
            )

            is_overlap = current_start < existing_end and current_end > existing_start

            if is_overlap:
                existing_start_local = timezone.localtime(existing_start)
                existing_end_local = timezone.localtime(existing_end)

                raise ValidationError(
                    f"Phòng {self.room.name} đã có suất chiếu "
                    f"từ {existing_start_local.strftime('%d/%m/%Y %H:%M')} "
                    f"đến {existing_end_local.strftime('%H:%M')}. "
                    f"Vui lòng chọn thời gian khác."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "start_time"],
                name="unique_showtime_room_start_time"
            )
        ]

    def __str__(self):
        return f"{self.movie.title} - {self.room.name} - {self.start_time}"


class Booking(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE)

    booking_code = models.CharField(max_length=20, unique=True)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    
    hold_expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.booking_code


class BookingSeat(models.Model):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="booking_seats"
    )

    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.booking.booking_code} - {self.seat}"


class Payment(models.Model):
    METHOD_CHOICES = (
        ("cash", "Pay at Cinema"),
        ("vnpay", "VNPay"),
        ("stripe", "Stripe"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="payment"
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.booking.booking_code} - {self.status}"


class Ticket(models.Model):
    STATUS_CHOICES = (
        ("valid", "Valid"),
        ("used", "Used"),
        ("cancelled", "Cancelled"),
    )

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="ticket"
    )
    qr_code = models.ImageField(upload_to="tickets/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="valid")
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.booking.booking_code}"


@receiver(post_save, sender=Room)
def create_room_seats(sender, instance, created, **kwargs):
    if created:
        instance.generate_seats()
