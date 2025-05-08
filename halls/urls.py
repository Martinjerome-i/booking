# halls/urls.py
from django.urls import path, re_path
from django.shortcuts import redirect
from . import views
from django.contrib.auth.views import LogoutView

# Function to redirect root URL to halls/1/book/
def redirect_to_hall_booking(request):
    return redirect('stall_booking', hall_id=1)

urlpatterns = [
    # Root URL now redirects to hall 1 booking page
    path('', redirect_to_hall_booking, name='root'),
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
    path('booking/<int:booking_id>/update-status/', views.update_booking_status, name='update_booking_status'),
    path('halls/<int:hall_id>/combos/', views.get_combos, name='get_combos'),
    path('halls/<int:hall_id>/create-combo/', views.create_combo, name='create_combo'),
    path('combo/<int:combo_id>/edit/', views.edit_combo, name='edit_combo'),
    path('combo/<int:combo_id>/delete/', views.delete_combo, name='delete_combo'),
    path('cancel-booking/', views.cancel_booking_process, name='cancel_booking_process'),

    path('admin_halls/<int:hall_id>/manage/', views.admin_stall_management, name='admin_stall_management'),
    path('admin_stall/<int:stall_id>/update-status/', views.admin_update_stall_status, name='admin_update_stall_status'),
    path('admin_booking/<int:booking_id>/delete/', views.admin_delete_booking, name='admin_delete_booking'),

    # re_path(r'^.*\.*', views.pages, name='pages'),

    path('adminLogin/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_booking/', views.admin_booking, name='admin_booking'),
    path('notifications/', views.get_notifications, name='get_notifications'),
    # path('logout/', LogoutView.as_view(), name='logout'),
    path('api/verify_token/', views.verify_token, name='verify_token'),
]