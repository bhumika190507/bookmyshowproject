from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone
from datetime import timedelta


class Movie(models.Model):

    GENRE_CHOICES = [
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Thriller', 'Thriller'),
        ('Romance', 'Romance'),
        ('Horror', 'Horror'),
    ]

    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Hindi', 'Hindi'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),
    ]

    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)

    genre = models.CharField(
        max_length=20,
        choices=GENRE_CHOICES
    )

    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES
    )
    
    trailer_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie,on_delete=models.CASCADE,related_name='theaters')
    time= models.DateTimeField()

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'

class Seat(models.Model):
    theater = models.ForeignKey(Theater,on_delete=models.CASCADE,related_name='seats')
    seat_number = models.CharField(max_length=10)

    is_booked = models.BooleanField(default=False)

    # NEW
    is_reserved = models.BooleanField(default=False)
    reserved_at = models.DateTimeField(null=True, blank=True)

    def is_reservation_expired(self):
        if self.reserved_at:
            return timezone.now() > self.reserved_at + timedelta(minutes=5)
        return False

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)

    total_amount = models.IntegerField(default=200)

    razorpay_order_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=500, blank=True, null=True)

    is_paid = models.BooleanField(default=False)

    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking by {self.user.username} for {self.seat.seat_number}'