from ntpath import join
from django.shortcuts import render, redirect ,get_object_or_404
from .models import Movie,Theater,Seat,Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta


def send_booking_email(user, movie, theater, seats):
    seat_numbers = ", ".join(seats)

    subject = "🎟️ Your Movie Ticket is Confirmed!"

    message = f"""
Hi {user.username} 👋,

Your booking is CONFIRMED ✅

🎬 Movie: {movie.name}
🏢 Theater: {theater.name}
💺 Seats: {seat_numbers}

Enjoy your movie 🍿
Thanks for booking with BookMySeat ❤️
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def movie_list(request):
    movies = Movie.objects.all()

    search_query = request.GET.get('search')
    genre = request.GET.get('genre')
    language = request.GET.get('language')

    if search_query:
        movies = movies.filter(name__icontains=search_query)

    if genre:
        movies = movies.filter(genre=genre)

    if language:
        movies = movies.filter(language=language)

    genres = Movie.objects.values_list('genre', flat=True).distinct()
    languages = Movie.objects.values_list('language', flat=True).distinct()

    context = {
        'movies': movies,
        'genres': genres,
        'languages': languages,
        'selected_genre': genre,
        'selected_language': language,
        'search_query': search_query,
    }

    return render(request, 'movies/movie_list.html', context)

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    return render(request, 'movies/movie_detail.html', {'movie': movie})


def theater_list(request,movie_id):
    movie = get_object_or_404(Movie,id=movie_id)
    theater=Theater.objects.filter(movie=movie)
    return render(request,'movies/theater_list.html',{'movie':movie,'theaters':theater})

def release_expired_seats():
    expired_time = timezone.now() - timedelta(minutes=5)

    expired_seats = Seat.objects.filter(
        is_reserved=True,
        reserved_at__lt=expired_time
    )

    for seat in expired_seats:
        seat.is_reserved = False
        seat.reserved_at = None
        seat.save()

@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    release_expired_seats() 
    seats = Seat.objects.filter(theater=theater)

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')

        if not selected_seats:
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                'seats': seats,
                'error': "No seat selected"
            })

        # For simplicity, allow only one seat per payment
        seat_id = selected_seats[0]
        seat = get_object_or_404(Seat, id=seat_id, theater=theater)

        if seat.is_booked or (seat.is_reserved and not seat.is_reservation_expired()):
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                'seats': seats,
                'error': "Seat already booked"
            })
        seat.is_reserved = True
        seat.reserved_at = timezone.now()
        seat.save()
        booking = Booking.objects.create(
            user=request.user,
            seat=seat,
            movie=theater.movie,
            theater=theater,
            total_amount=200  # change ticket price if needed
        )

        # DO NOT mark seat as booked yet
        # DO NOT send email yet

        return redirect('create_payment', booking_id=booking.id)

    return render(request, 'movies/seat_selection.html', {
        'theater': theater,
        'seats': seats
    })
    
    
# helpeer function
def send_booking_confirmation_email(user, booking):
    subject = "🎟 Your Movie Ticket is Confirmed!"

    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [user.email]

    html_content = render_to_string(
        'movies/booking_email.html',
        {
            'user': user,
            'booking': booking
        }
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body='Your booking is confirmed.',
        from_email=from_email,
        to=to_email
    )

    email.attach_alternative(html_content, "text/html")
    email.send()

@login_required
def create_payment(request, booking_id):
    booking = Booking.objects.get(id=booking_id)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    amount = booking.total_amount * 100  # Razorpay works in paise

    payment = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    booking.razorpay_order_id = payment["id"]
    booking.save()

    context = {
        "booking": booking,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "order_id": payment["id"],
        "amount": amount,
    }

    return render(request, "movies/payment.html", context)

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        data = request.POST

        order_id = data.get("razorpay_order_id")
        payment_id = data.get("razorpay_payment_id")
        signature = data.get("razorpay_signature")

        booking = Booking.objects.get(razorpay_order_id=order_id)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })

            booking.razorpay_payment_id = payment_id
            booking.razorpay_signature = signature
            booking.is_paid = True
            booking.save()

            # BOOK THE SEAT
            seat = booking.seat
            seat.is_booked = True
            seat.is_reserved = False
            seat.reserved_at = None
            seat.save()
            send_booking_confirmation_email(booking.user, booking)

            return render(request, "movies/payment_success.html")
        except:
            return render(request, "movies/payment_failed.html")
from django.db.models import Sum, Count
from django.contrib.admin.views.decorators import staff_member_required

from django.db.models import Sum, Count
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_dashboard(request):
    bookings = Booking.objects.filter(is_paid=True)

    # 🔍 Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    movie_filter = request.GET.get('movie')

    if start_date and end_date:
        bookings = bookings.filter(booked_at__date__range=[start_date, end_date])

    if movie_filter:
        bookings = bookings.filter(movie__id=movie_filter)

    # 💰 Revenue
    total_revenue = bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # 📦 Bookings
    total_bookings = bookings.count()

    # 🎬 Popular Movies
    popular_movies = (
        bookings.values('movie__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    # 🏢 Theaters
    busiest_theaters = (
        bookings.values('theater__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    movies = Movie.objects.all()

    return render(request, 'movies/admin_dashboard.html', {
        'total_revenue': total_revenue,
        'total_bookings': total_bookings,
        'popular_movies': popular_movies,
        'busiest_theaters': busiest_theaters,
        'movies': movies,
    })
    
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_bookings(request):
    bookings = Booking.objects.filter(is_paid=True).order_by('-booked_at')

    return render(request, 'movies/admin_bookings.html', {
        'bookings': bookings
    })
    
@staff_member_required
def admin_movies(request):
    movies = Movie.objects.all()

    movie_data = []

    for movie in movies:
        bookings = Booking.objects.filter(movie=movie, is_paid=True)

        total_bookings = bookings.count()
        total_revenue = bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        movie_data.append({
            'name': movie.name,
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
        })

    return render(request, 'movies/admin_movies.html', {
        'movie_data': movie_data
    })