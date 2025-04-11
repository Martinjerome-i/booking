# halls/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Hall, Stall, Booking
from .forms import BookingForm
import json
import uuid


def index(request):
    halls = Hall.objects.all()
    return render(request, 'halls/index.html', {'halls': halls})


def hall_detail(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    stalls = hall.stalls.all()
    return render(request, 'halls/hall_detail.html', {'hall': hall, 'stalls': stalls})


def create_hall(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        length = int(request.POST.get('length'))
        breadth = int(request.POST.get('breadth'))

        hall = Hall.objects.create(name=name, length=length, breadth=breadth)
        return redirect('hall_detail', hall_id=hall.id)

    return render(request, 'halls/create_hall.html')


def create_stall(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)

    if request.method == 'POST':
        data = json.loads(request.body)
        stall_number = data.get('stall_number')
        selected_boxes = data.get('selected_boxes', [])
        price = data.get('price', 0)

        # Check if a stall with the same number already exists in this hall
        if Stall.objects.filter(hall=hall, stall_number=stall_number).exists():
            return JsonResponse({
                'success': False, 
                'error': 'A stall with this number already exists in this hall.'
            }, status=400)

        # Calculate the dimensions of the stall
        x_coordinates = [box['x'] for box in selected_boxes]
        y_coordinates = [box['y'] for box in selected_boxes]

        x_start = min(x_coordinates) if x_coordinates else 0
        y_start = min(y_coordinates) if y_coordinates else 0
        x_end = max(x_coordinates) if x_coordinates else 0
        y_end = max(y_coordinates) if y_coordinates else 0

        width = (x_end - x_start) + 1
        height = (y_end - y_start) + 1

        # Create the stall
        stall = Stall.objects.create(
            hall=hall,
            stall_number=stall_number,
            x_start=x_start,
            y_start=y_start,
            width=width,
            height=height,
            selected_boxes=selected_boxes,
            price=price
        )

        return JsonResponse({'success': True, 'stall_id': stall.id})

    return render(request, 'halls/create_stall.html', {'hall': hall})


def get_hall_data(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    stalls = hall.stalls.all()

    stall_data = []
    for stall in stalls:
        stall_data.append({
            'id': stall.id,
            'stall_number': stall.stall_number,
            'selected_boxes': stall.selected_boxes,
            'status': stall.status,
            'price': float(stall.price),
        })

    return JsonResponse({
        'hall': {
            'id': hall.id,
            'name': hall.name,
            'length': hall.length,
            'breadth': hall.breadth,
        },
        'stalls': stall_data
    })

def delete_stall(request, hall_id, stall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    stall = get_object_or_404(Stall, id=stall_id, hall=hall)
    
    # Delete the stall
    stall.delete()
    
    # Redirect back to the hall detail page
    return redirect('hall_detail', hall_id=hall_id)


def edit_stall(request, hall_id, stall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    stall = get_object_or_404(Stall, id=stall_id, hall=hall)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        stall_number = data.get('stall_number')
        price = data.get('price')
        
        if not stall_number:
            return JsonResponse({'success': False, 'error': 'Stall number is required'})
        
        # Check if a stall with the same number already exists in this hall
        # Exclude the current stall from the check
        if Stall.objects.filter(hall=hall, stall_number=stall_number).exclude(id=stall_id).exists():
            return JsonResponse({
                'success': False, 
                'error': 'A stall with this number already exists in this hall.'
            }, status=400)
        
        stall.stall_number = stall_number
        if price is not None:
            stall.price = price
        stall.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# Booking Related Views
def stall_booking(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    return render(request, 'halls/stall_booking.html', {'hall': hall})


def get_stall_details(request, stall_id):
    stall = get_object_or_404(Stall, id=stall_id)
    
    # Check if stall is available for booking
    if stall.status != 'available':
        return JsonResponse({
            'success': False,
            'error': f'This stall is already {stall.status}.'
        }, status=400)
    
    return JsonResponse({
        'success': True,
        'stall': {
            'id': stall.id,
            'stall_number': stall.stall_number,
            'width': stall.width,
            'height': stall.height,
            'area': stall.area,
            'price': float(stall.price),
            'hall_name': stall.hall.name,
        }
    })


def book_stall(request, stall_id):
    stall = get_object_or_404(Stall, id=stall_id)
    
    # Check if stall is already booked
    if stall.status != 'available':
        return redirect('stall_booking', hall_id=stall.hall.id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.stall = stall
            booking.save()
            
            # Send confirmation email
            try:
                send_booking_confirmation(booking)
            except:
                # Log error but continue
                pass
            
            return redirect('booking_confirmation', booking_id=booking.id)
    else:
        form = BookingForm()
    
    return render(request, 'halls/book_stall.html', {
        'form': form,
        'stall': stall,
        'hall': stall.hall
    })


def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'halls/booking_confirmation.html', {'booking': booking})


def manage_bookings(request):
    bookings = Booking.objects.all().order_by('-booking_date')
    return render(request, 'halls/manage_bookings.html', {'bookings': bookings})


@require_POST
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    status = request.POST.get('status')
    
    if status in [s[0] for s in Booking.STATUS_CHOICES]:
        booking.status = status
        booking.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid status'})


def send_booking_confirmation(booking):
    subject = f'Booking Confirmation - {booking.booking_reference}'
    message = f'''
    Dear {booking.customer_name},
    
    Thank you for booking Stall {booking.stall.stall_number} in {booking.stall.hall.name}.
    
    Booking Reference: {booking.booking_reference}
    Event Dates: {booking.event_start_date} to {booking.event_end_date}
    Stall Size: {booking.stall.width}m x {booking.stall.height}m ({booking.stall.area}m²)
    Price: ${booking.stall.price}
    
    Your booking status is currently: {booking.get_status_display()}
    
    Please keep this reference for future communications.
    
    Regards,
    The Exhibition Team
    '''
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [booking.customer_email]
    
    send_mail(subject, message, from_email, recipient_list)