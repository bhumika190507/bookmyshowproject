from django.urls import path
from . import views
from .views import admin_dashboard

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('<int:movie_id>/theaters/', views.theater_list, name='theater_list'),
    path('theater/<int:theater_id>/seats/book/', views.book_seats, name='book_seats'),
    
    # 💳 Payment URLs
    path('payment/<int:booking_id>/', views.create_payment, name='create_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    path('admin-bookings/', views.admin_bookings, name='admin_bookings'),
    
    path('admin-movies/', views.admin_movies, name='admin_movies'),
    
]