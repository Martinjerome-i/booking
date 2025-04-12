from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Hall, Stall, Booking, ComboStall
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
    combos = hall.combos.all()

    stall_data = []
    for stall in stalls:
        stall_data.append({
            'id': stall.id,
            'stall_number': stall.stall_number,
            'selected_boxes': stall.selected_boxes,
            'status': stall.status,
            'price': float(stall.price),
        })

    combo_data = []
    for combo in combos:
        combo_stalls = list(combo.stalls.values_list('id', flat=True))
        combo_data.append({
            'id': combo.id,
            'name': combo.name,
            'description': combo.description or '',
            'stall_ids': combo_stalls,
            'price': float(combo.total_price),
        })

    return JsonResponse({
        'hall': {
            'id': hall.id,
            'name': hall.name,
            'length': hall.length,
            'breadth': hall.breadth,
        },
        'stalls': stall_data,
        'combos': combo_data
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


def book_stall(request):
    """
    View for booking multiple stalls at once
    """
    stall_ids = request.GET.get('stall_ids', '').split(',')
    stall_ids = [id for id in stall_ids if id]  # Filter out empty strings
    
    if not stall_ids:
        return redirect('index')
    
    # Get all stalls
    stalls = Stall.objects.filter(id__in=stall_ids)
    
    # Check if any stall is already booked
    unavailable_stalls = stalls.exclude(status='available')
    if unavailable_stalls.exists():
        # Some stalls are not available, redirect back to the booking page
        hall_id = stalls.first().hall.id if stalls.exists() else 1
        return redirect('stall_booking', hall_id=hall_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            # Create booking but don't save stall relationship yet
            booking = form.save(commit=False)
            booking.status = 'booked'  # Directly set to booked status
            booking.save()  # Save to generate ID
            
            # Now add all stalls to the booking
            booking.stalls.set(stalls)
            
            # Update stall status to booked
            stalls.update(status='booked')
            
            # NOTE: Email sending has been removed as requested
            
            return redirect('booking_confirmation', booking_id=booking.id)
    else:
        form = BookingForm()
    
    # Get the hall info from the first stall
    hall = stalls.first().hall if stalls.exists() else None
    
    # Calculate total price
    total_price = sum(stall.price for stall in stalls)
    
    return render(request, 'halls/book_stall.html', {
        'form': form,
        'stalls': stalls,
        'hall': hall,
        'total_price': total_price
    })


def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Calculate the total price of all stalls
    stalls = booking.stalls.all()
    total_price = sum(stall.price for stall in stalls)
    
    # Get the hall ID if there are stalls
    hall_id = stalls.first().hall.id if stalls.exists() else 1
    
    return render(request, 'halls/booking_confirmation.html', {
        'booking': booking,
        'stalls': stalls,
        'total_price': total_price,
        'hall_id': hall_id
    })


def manage_bookings(request):
    bookings = Booking.objects.all().order_by('-booking_date')
    return render(request, 'halls/manage_bookings.html', {'bookings': bookings})


@require_POST
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    status = request.POST.get('status')
    
    if status in [s[0] for s in Booking.STATUS_CHOICES]:
        booking.status = status
        booking.save()  # This will update the stall statuses through the save method
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid status'})


# The email function is retained but not called anywhere, as requested
def send_booking_confirmation(booking):
    subject = f'Booking Confirmation - {booking.booking_reference}'
    
    # Get all stalls in this booking
    stalls = booking.stalls.all()
    
    # Generate stall details for the email
    stall_details = ""
    total_price = 0
    
    if stalls.exists():
        for stall in stalls:
            stall_details += f"""
            Stall #{stall.stall_number} in {stall.hall.name}
            Size: {stall.width}m x {stall.height}m ({stall.area}m²)
            Price: ${stall.price}
            
            """
            total_price += stall.price
    else:
        stall_details = "No stalls in this booking."
    
    message = f"""
    Dear {booking.customer_name},
    
    Thank you for your booking at our exhibition.
    
    Booking Reference: {booking.booking_reference}
    Booking Date: {booking.booking_date.strftime('%B %d, %Y')}
    
    STALL DETAILS:
    {stall_details}
    
    Total Price: ${total_price}
    
    Your booking status is: {booking.get_status_display()}
    
    Please keep this reference for future communications.
    
    Regards,
    The Exhibition Team
    """
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [booking.customer_email]
    
    send_mail(subject, message, from_email, recipient_list)


# Combo stall related views
def create_combo(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description', '')
        stall_ids = data.get('stall_ids', [])
        price = data.get('price')
        
        # Validate
        if not name:
            return JsonResponse({'success': False, 'error': 'Combo name is required'})
        if not stall_ids:
            return JsonResponse({'success': False, 'error': 'You must select at least one stall'})
            
        # Create combo
        combo = ComboStall.objects.create(
            name=name,
            hall=hall,
            description=description,
            price=price if price else None
        )
        
        # Add stalls to combo
        stalls = Stall.objects.filter(id__in=stall_ids, hall=hall)
        combo.stalls.set(stalls)
        
        return JsonResponse({'success': True, 'combo_id': combo.id})
        
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def edit_combo(request, combo_id):
    combo = get_object_or_404(ComboStall, id=combo_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description', '')
        stall_ids = data.get('stall_ids', [])
        price = data.get('price')
        
        # Validate
        if not name:
            return JsonResponse({'success': False, 'error': 'Combo name is required'})
        if not stall_ids:
            return JsonResponse({'success': False, 'error': 'You must select at least one stall'})
            
        # Update combo
        combo.name = name
        combo.description = description
        combo.price = price if price else None
        combo.save()
        
        # Update stalls in combo
        stalls = Stall.objects.filter(id__in=stall_ids, hall=combo.hall)
        combo.stalls.set(stalls)
        
        return JsonResponse({'success': True})
        
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def delete_combo(request, combo_id):
    combo = get_object_or_404(ComboStall, id=combo_id)
    hall_id = combo.hall.id
    combo.delete()
    return redirect('hall_detail', hall_id=hall_id)

def get_combos(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    combos = hall.combos.all()
    
    combo_data = []
    for combo in combos:
        stalls = list(combo.stalls.values('id', 'stall_number'))
        combo_data.append({
            'id': combo.id,
            'name': combo.name,
            'description': combo.description,
            'stalls': stalls,
            'price': float(combo.total_price),
            'custom_price': float(combo.price) if combo.price else None,
            'stall_count': combo.stall_count
        })
    
    return JsonResponse({'success': True, 'combos': combo_data})