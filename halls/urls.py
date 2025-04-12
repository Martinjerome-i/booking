# halls/urls.py
from django.urls import path
from django.shortcuts import redirect
from . import views

# Function to redirect root URL to halls/1/book/
def redirect_to_hall_booking(request):
    return redirect('stall_booking', hall_id=1)

urlpatterns = [
    # Root URL now redirects to hall 1 booking page
    path('', redirect_to_hall_booking, name='root'),
    
    # Existing URLs (index view can remain as a separate page if needed)
    path('index/', views.index, name='index'),
    path('halls/create/', views.create_hall, name='create_hall'),
    path('halls/<int:hall_id>/', views.hall_detail, name='hall_detail'),
    path('halls/<int:hall_id>/create-stall/', views.create_stall, name='create_stall'),
    path('halls/<int:hall_id>/data/', views.get_hall_data, name='get_hall_data'),
    path('halls/<int:hall_id>/stall/<int:stall_id>/delete/', views.delete_stall, name='delete_stall'),
    path('halls/<int:hall_id>/stall/<int:stall_id>/edit/', views.edit_stall, name='edit_stall'),
    
    # Booking URLs
    path('halls/<int:hall_id>/book/', views.stall_booking, name='stall_booking'),
    path('stall/<int:stall_id>/details/', views.get_stall_details, name='get_stall_details'),
    path('stalls/book/', views.book_stall, name='book_stalls'),
    path('booking/<int:booking_id>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    path('bookings/', views.manage_bookings, name='manage_bookings'),
    path('booking/<int:booking_id>/update-status/', views.update_booking_status, name='update_booking_status'),
    path('halls/<int:hall_id>/combos/', views.get_combos, name='get_combos'),
    path('halls/<int:hall_id>/create-combo/', views.create_combo, name='create_combo'),
    path('combo/<int:combo_id>/edit/', views.edit_combo, name='edit_combo'),
    path('combo/<int:combo_id>/delete/', views.delete_combo, name='delete_combo'),
]