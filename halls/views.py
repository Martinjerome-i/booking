import jwt
import datetime
from functools import wraps
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Hall, Stall, Booking, ComboStall
from django.views.decorators.http import require_POST
from .forms import BookingForm
import json
import uuid
from django.views.decorators.csrf import csrf_exempt
from functools import wraps
from django.contrib.auth.models import User
import decimal


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        request = args[0]
        token = request.COOKIES.get('jwt_token')
        
        if not token:
            return redirect('admin_login')
            
        try:
            # Decode token
            data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        except:
            return redirect('admin_login')
            
        return f(*args, **kwargs)
    return decorated

# Admin Login View
def admin_login(request):
    error_message = None
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        print(f"Login attempt with email: {email}")
        
        # First try to find user by email
        from django.contrib.auth.models import User
        try:
            # Check if a user with this email exists
            users = User.objects.filter(email=email)
            if users.exists():
                user_obj = users.first()
                print(f"Found user by email: {user_obj.username}, is_staff={user_obj.is_staff}, is_superuser={user_obj.is_superuser}")
                
                # Try authenticating with the found username
                user = authenticate(username=user_obj.username, password=password)
            else:
                print(f"No user found with email: {email}")
                # Try authenticating directly with email as username
                user = authenticate(username=email, password=password)
        except Exception as e:
            print(f"Error finding user: {e}")
            user = authenticate(username=email, password=password)
            
        print(f"Authentication result: {user}")
        
        if user is not None and user.is_staff:
            # Generate JWT token
            token_payload = {
                'user_id': user.id,
                'username': user.username,
                'exp': datetime.datetime.utcnow() + settings.JWT_EXPIRATION_DELTA
            }
            
            try:
                token = jwt.encode(token_payload, settings.JWT_SECRET, algorithm="HS256")
                print("JWT token generation successful")
            except Exception as e:
                print(f"JWT token generation error: {e}")
                error_message = "Error generating authentication token"
                return render(request, 'home/login.html', {'error_message': error_message})
            
            # Login user in Django session
            login(request, user)
            
            # Create response with redirect
            response = redirect('admin_dashboard')
            
            # Set JWT token in cookie
            response.set_cookie('jwt_token', token, httponly=True)
            
            return response
        else:
            if user is not None:
                error_message = f"User found but is not staff (is_staff={user.is_staff})"
            else:
                error_message = "Invalid credentials or not authorized as admin"
    
    return render(request, 'home/login.html', {'error_message': error_message})

# Admin Logout View
def admin_logout(request):
    logout(request)
    response = redirect('admin_login')
    response.delete_cookie('jwt_token')
    return response

# Verify Token API endpoint
@csrf_exempt
def verify_token(request):
    token = request.COOKIES.get('jwt_token')
    
    if not token:
        return JsonResponse({'valid': False}, status=401)
        
    try:
        # Decode token
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return JsonResponse({'valid': True, 'user': data['username']})
    except:
        return JsonResponse({'valid': False}, status=401)


# @login_required(login_url="/login/")
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]

        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


def admin_dashboard(request):
    # Get counts for various statistics
    from django.db.models import Sum, Count
    from datetime import timedelta
    from django.utils import timezone
    
    # Date range for "recent" stats (30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    sixty_days_ago = timezone.now() - timedelta(days=60)
    
    # Get all bookings in last 30 days
    recent_bookings = Booking.objects.filter(booking_date__gte=thirty_days_ago)
    
    # Get bookings from previous 30 days for trend comparison
    previous_bookings = Booking.objects.filter(
        booking_date__gte=sixty_days_ago,
        booking_date__lt=thirty_days_ago
    )
    
    # Get counts
    total_bookings_count = recent_bookings.count()
    previous_bookings_count = previous_bookings.count()
    
    # Calculate booking trend (percentage increase/decrease)
    booking_trend = 0
    if previous_bookings_count > 0:
        booking_trend = ((total_bookings_count - previous_bookings_count) / previous_bookings_count) * 100
    
    # Get stall counts by status
    stall_status_counts = {
        'available': Stall.objects.filter(status='available').count(),
        'booked': Stall.objects.filter(status='booked').count(),
        'blocked': Stall.objects.filter(status='blocked').count()
    }
    total_stalls = sum(stall_status_counts.values())
    
    # Calculate total revenue from recent bookings
    # First, get all stalls associated with recent bookings
    booked_stalls = Stall.objects.filter(bookings__in=recent_bookings)
    total_revenue = sum(stall.price for stall in booked_stalls)
    
    # Get previous period revenue for trend calculation
    previous_booked_stalls = Stall.objects.filter(bookings__in=previous_bookings)
    previous_revenue = sum(stall.price for stall in previous_booked_stalls)
    
    # Calculate revenue trend
    revenue_trend = 0
    if previous_revenue > 0:
        revenue_trend = ((total_revenue - previous_revenue) / previous_revenue) * 100
    
    # Get latest 5 bookings for the recent bookings table and notifications
    latest_bookings = Booking.objects.all().order_by('-booking_date')[:5]
    
    # Check if there are new bookings (less than 24 hours old)
    one_day_ago = timezone.now() - timedelta(hours=24)
    has_new_notifications = Booking.objects.filter(booking_date__gte=one_day_ago).exists()
    
    # Prepare booking data for the template
    booking_data = []
    notification_data = []
    
    for booking in latest_bookings:
        # Get all stall numbers for this booking
        stall_numbers = [stall.stall_number for stall in booking.stalls.all()]
        stall_numbers_str = ", ".join(stall_numbers)
        
        # Calculate time difference for notifications
        time_diff = timezone.now() - booking.booking_date
        hours_ago = time_diff.total_seconds() // 3600
        
        if hours_ago < 1:
            time_display = "a few moments ago"
        elif hours_ago < 24:
            time_display = f"{int(hours_ago)} hrs ago"
        else:
            days = time_diff.days
            time_display = f"{days} d ago"
        
        # Check if this is a new notification (less than 24 hours)
        is_new = booking.booking_date >= one_day_ago
        
        booking_data.append({
            'id': booking.id,
            'reference': booking.booking_reference,
            'customer': booking.customer_name,
            'date': booking.booking_date,
            'stall_count': booking.stalls.count(),
            'stall_numbers': stall_numbers,
            'status': booking.status,
            'payment_status': booking.payment_status
        })
        
        # Add notification data
        notification_data.append({
            'id': booking.id,
            'customer_name': booking.customer_name,
            'time_display': time_display,
            'message': f"Booked stall(s): {stall_numbers_str}",
            'is_new': is_new
        })
    
    # Monthly revenue data (for the chart)
    current_year = timezone.now().year
    monthly_revenue = []
    
    for month in range(1, 13):
        # Get bookings for this month
        month_bookings = Booking.objects.filter(
            booking_date__year=current_year,
            booking_date__month=month
        )
        # Get stalls booked in this month
        month_stalls = Stall.objects.filter(bookings__in=month_bookings)
        # Calculate total revenue
        month_revenue = sum(stall.price for stall in month_stalls)
        
        # Get month name
        import calendar
        month_name = calendar.month_abbr[month]
        
        monthly_revenue.append({
            'month': month_name,
            'revenue': float(month_revenue)
        })
    
    context = {
        'stats': {
            'total_bookings': total_bookings_count,
            'booking_trend': round(booking_trend),
            'total_revenue': float(total_revenue),
            'revenue_trend': round(revenue_trend),
            'available_stalls': stall_status_counts['available'],
            'total_stalls': total_stalls,
            'stall_status': stall_status_counts,
        },
        'recent_bookings': booking_data,
        'notifications': notification_data,
        'has_new_notifications': has_new_notifications,
        'monthly_revenue': monthly_revenue
    }
    
    return render(request, 'home/dashboard.html', context)


def get_notifications(request):
    """Separate view for handling booking notifications"""
    # Get latest 5 bookings for the notifications
    latest_bookings = Booking.objects.all().order_by('-booking_date')[:5]
    
    booking_notifications = []
    for booking in latest_bookings:
        # Get all stall numbers for this booking as a comma-separated string
        stall_numbers = ", ".join([stall.stall_number for stall in booking.stalls.all()])
        
        # Calculate time difference for display
        time_diff = timezone.now() - booking.booking_date
        if time_diff.days > 0:
            time_display = f"{time_diff.days} days ago"
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            time_display = f"{hours} hrs ago"
        else:
            minutes = time_diff.seconds // 60
            time_display = "a few moments ago" if minutes < 5 else f"{minutes} mins ago"
        
        # Check if this is a new notification (less than 24 hours)
        one_day_ago = timezone.now() - timedelta(hours=24)
        is_new = booking.booking_date >= one_day_ago
        
        booking_notifications.append({
            'id': booking.id,
            'customer_name': booking.customer_name,
            'stall_numbers': stall_numbers,
            'time_display': time_display,
            'booking_date': booking.booking_date,
            'status': booking.status,
            'is_new': is_new
        })
    
    # Check if there are new bookings (less than 24 hours old)
    has_new_notifications = any(notification['is_new'] for notification in booking_notifications)
    
    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'booking_notifications': booking_notifications,
            'has_new_notifications': has_new_notifications
        })
    
    # Otherwise render a template
    return render(request, 'home/notifications.html', {
        'booking_notifications': booking_notifications,
        'has_new_notifications': has_new_notifications
    })


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


# Next, let's create a function to calculate discounts based on the number of stalls
def calculate_discounted_price(stall_count, total_price):
    """
    Calculate discounted price based on number of stalls
    - 1 stall: No discount
    - 2 stalls: Flat ₹5,000 discount
    - 3+ stalls: ₹5,000 discount per stall
    """
    if stall_count == 1:
        # No discount
        return total_price
    elif stall_count == 2:
        # Flat ₹5,000 discount
        discount = decimal.Decimal('5000')
        return total_price - discount
    else:  # 3 or more stalls
        # ₹5,000 discount per stall
        discount = decimal.Decimal('5000') * stall_count
        return total_price - discount


def book_stall(request):
    """
    View for booking multiple stalls at once with discount application
    """
    from django.shortcuts import render, redirect, get_object_or_404
    from .forms import BookingForm  # Make sure to import the form
    
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
    
    # Separate regular stalls and combo stalls
    regular_stalls = []
    combo_stalls = []
    
    for stall in stalls:
        # Check if this stall is part of a combo
        if hasattr(stall, 'combos') and stall.combos.exists():
            combo_stalls.append(stall)
        else:
            regular_stalls.append(stall)
    
    # Calculate regular stall price with applicable discount
    regular_stall_count = len(regular_stalls)
    regular_stall_base_price = sum(stall.price for stall in regular_stalls)
    
    # Apply the updated discount logic
    if regular_stall_count == 1:
        discount_amount = 0
        discounted_regular_price = regular_stall_base_price
    elif regular_stall_count == 2:
        discount_amount = decimal.Decimal('5000')
        discounted_regular_price = regular_stall_base_price - discount_amount
    else:  # 3 or more stalls
        discount_amount = decimal.Decimal('5000') * regular_stall_count
        discounted_regular_price = regular_stall_base_price - discount_amount
    
    # Combo stalls have a fixed price of 130,000 for the entire combo package
    combo_stall_price = decimal.Decimal('130000.00') if combo_stalls else decimal.Decimal('0')
    
    # Total price
    total_price = discounted_regular_price + combo_stall_price

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            # Create booking but don't save stall relationship yet
            booking = form.save(commit=False)
            booking.status = 'booked'  # Directly set to booked status
            booking.total_amount = total_price  # Save the total amount
            booking.save()  # Save to generate ID
            
            # Now add all stalls to the booking
            booking.stalls.set(stalls)
            
            # Update stall status to booked
            stalls.update(status='booked')
            
            return redirect('booking_confirmation', booking_id=booking.id)
    else:
        form = BookingForm()
    
    # Get the hall info from the first stall
    hall = stalls.first().hall if stalls.exists() else None
    
    # Calculate discount percentage for display purposes
    discount_percentage = 0
    if regular_stall_base_price > 0 and discount_amount > 0:
        discount_percentage = (discount_amount / regular_stall_base_price) * 100
    
    return render(request, 'halls/book_stall.html', {
        'form': form,
        'stalls': stalls,
        'hall': hall,
        'total_price': total_price,
        'regular_stall_count': regular_stall_count,
        'regular_stall_base_price': regular_stall_base_price,
        'discounted_regular_price': discounted_regular_price,
        'combo_stall_price': combo_stall_price,
        'discount_amount': discount_amount,
        'discount_percentage': discount_percentage,
        'regular_stalls': regular_stalls,
        'combo_stalls': combo_stalls
    })


def booking_confirmation(request, booking_id):
    """
    View for booking confirmation with updated discount calculations
    """
    from django.shortcuts import render, get_object_or_404
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Get all stalls in the booking
    stalls = booking.stalls.all()
    
    # Separate regular stalls and combo stalls
    regular_stalls = []
    combo_stalls = []
    
    for stall in stalls:
        # Check if this stall is part of a combo
        if hasattr(stall, 'combos') and stall.combos.exists():
            combo_stalls.append(stall)
        else:
            regular_stalls.append(stall)
    
    # Calculate regular stall price with applicable discount
    regular_stall_count = len(regular_stalls)
    regular_stall_base_price = sum(stall.price for stall in regular_stalls)
    
    # Apply the updated discount logic
    if regular_stall_count == 1:
        discount_amount = 0
        discounted_regular_price = regular_stall_base_price
    elif regular_stall_count == 2:
        discount_amount = decimal.Decimal('5000')
        discounted_regular_price = regular_stall_base_price - discount_amount
    else:  # 3 or more stalls
        discount_amount = decimal.Decimal('5000') * regular_stall_count
        discounted_regular_price = regular_stall_base_price - discount_amount
    
    # Combo stalls have a fixed price of 130,000 for the entire combo package
    combo_stall_price = decimal.Decimal('130000.00') if combo_stalls else decimal.Decimal('0')
    
    # Use the total_amount from the booking model
    total_price = booking.total_amount
    
    # Calculate discount percentage for display purposes
    discount_percentage = 0
    if regular_stall_base_price > 0 and discount_amount > 0:
        discount_percentage = (discount_amount / regular_stall_base_price) * 100
    
    # Get the hall ID if there are stalls
    hall_id = stalls.first().hall.id if stalls.exists() else 1
    
    return render(request, 'halls/booking_confirmation.html', {
        'booking': booking,
        'stalls': stalls,
        'regular_stalls': regular_stalls,
        'combo_stalls': combo_stalls,
        'total_price': total_price,
        'hall_id': hall_id,
        'regular_stall_count': regular_stall_count,
        'regular_stall_base_price': regular_stall_base_price,
        'discounted_regular_price': discounted_regular_price,
        'combo_stall_price': combo_stall_price,
        'discount_amount': discount_amount,
        'discount_percentage': discount_percentage
    })


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


def admin_stall_management(request, hall_id):
    """
    View for admin to manage stalls (block/book) without authentication
    """
    hall = get_object_or_404(Hall, id=hall_id)
    stalls = hall.stalls.all()
    return render(request, 'home/manage_booking.html', {'hall': hall, 'stalls': stalls})

@require_POST
def admin_update_stall_status(request, stall_id):
    """
    API endpoint to update stall status from admin interface
    """
    stall = get_object_or_404(Stall, id=stall_id)
    status = request.POST.get('status')
    customer_name = request.POST.get('customer_name', '')
    customer_email = request.POST.get('customer_email', '')
    customer_phone = request.POST.get('customer_phone', '')
    company_name = request.POST.get('company_name', '')
    notes = request.POST.get('notes', '')
    booking_reference = request.POST.get('booking_reference', '')  # To link multiple stalls
    
    if status not in [s[0] for s in Stall.STATUS_CHOICES]:
        return JsonResponse({'success': False, 'error': 'Invalid status'})
    
    # Set this first to ensure the stall status is updated
    stall.status = status
    stall.save()
    
    # If booking the stall, create or update a booking record
    if status == 'booked' and customer_name and customer_email:
        if booking_reference:
            # Try to find existing booking with this reference
            try:
                booking = Booking.objects.get(booking_reference=booking_reference)
            except Booking.DoesNotExist:
                # Create new booking with provided reference
                booking = Booking.objects.create(
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    company_name=company_name,
                    notes=notes,
                    status='booked',
                    booking_reference=booking_reference,
                    is_admin_booking=True  # Mark as admin booking
                )
        else:
            # Create new booking with generated reference
            booking = Booking.objects.create(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                company_name=company_name,
                notes=notes,
                status='booked',
                is_admin_booking=True  # Mark as admin booking
            )
        
        # Add stall to booking
        booking.stalls.add(stall)
        
        # Calculate total amount with discount
        # This is now handled by the calculate_discounted_price function
        # which should respect that combo stalls are not eligible for discounts
        stalls_in_booking = booking.stalls.all()
        
        # First, identify combo stalls
        combo_stalls = []
        regular_stalls = []
        
        for s in stalls_in_booking:
            # Check if stall is part of a combo
            if hasattr(s, 'combos') and s.combos.exists():
                combo_stalls.append(s)
            else:
                regular_stalls.append(s)
        
        # Calculate price for combo stalls (no discount)
        combo_price = sum(s.price for s in combo_stalls)
        
        # Calculate price with discount for regular stalls
        regular_count = len(regular_stalls)
        regular_price = sum(s.price for s in regular_stalls)
        discounted_regular_price = calculate_discounted_price(regular_count, regular_price)
        
        # Total price is the sum of combo price and discounted regular price
        booking.total_amount = combo_price + discounted_regular_price
        booking.save()
        
        response_data = {
            'success': True, 
            'status': status,
            'status_display': dict(Stall.STATUS_CHOICES).get(status, status),
            'booking_reference': booking.booking_reference,
            'total_amount': float(booking.total_amount)
        }
    
    # If blocking the stall, create a 'blocked' booking record
    elif status == 'blocked':
        if booking_reference:
            # Try to find existing blocked booking with this reference
            try:
                booking = Booking.objects.get(booking_reference=booking_reference, status='blocked')
                booking.stalls.add(stall)
            except Booking.DoesNotExist:
                # Create new booking with provided reference
                booking = Booking.objects.create(
                    customer_name="Admin Blocked",
                    customer_email="admin@example.com",
                    customer_phone="N/A",
                    notes=notes or f"Blocked by admin on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    status='blocked',
                    booking_reference=booking_reference,
                    is_admin_booking=True  # Mark as admin booking
                )
                booking.stalls.add(stall)
        else:
            # Create new booking with generated reference
            booking = Booking.objects.create(
                customer_name="Admin Blocked",
                customer_email="admin@example.com",
                customer_phone="N/A",
                notes=notes or f"Blocked by admin on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                status='blocked',
                is_admin_booking=True  # Mark as admin booking
            )
            booking.stalls.add(stall)
        
        response_data = {
            'success': True, 
            'status': status,
            'status_display': dict(Stall.STATUS_CHOICES).get(status, status),
            'booking_reference': booking.booking_reference
        }
    
    # If unblocking (setting to available), find and update related bookings
    elif status == 'available':
        # Find any bookings that include this stall and mark them as cancelled
        affected_bookings = stall.bookings.filter(status__in=['blocked', 'booked'])
        
        for booking in affected_bookings:
            if booking.stalls.count() == 1:  # If this is the only stall in the booking
                booking.status = 'cancelled'
                booking.save()
            else:
                # If there are other stalls in this booking, just remove this stall
                booking.stalls.remove(stall)
                
                # Recalculate total amount with discount for remaining stalls
                # Similar logic as above for combo vs regular stalls
                stalls_in_booking = booking.stalls.all()
                
                # First, identify combo stalls
                combo_stalls = []
                regular_stalls = []
                
                for s in stalls_in_booking:
                    # Check if stall is part of a combo
                    if hasattr(s, 'combos') and s.combos.exists():
                        combo_stalls.append(s)
                    else:
                        regular_stalls.append(s)
                
                # Calculate price for combo stalls (no discount)
                combo_price = sum(s.price for s in combo_stalls)
                
                # Calculate price with discount for regular stalls
                regular_count = len(regular_stalls)
                regular_price = sum(s.price for s in regular_stalls)
                discounted_regular_price = calculate_discounted_price(regular_count, regular_price)
                
                # Total price is the sum of combo price and discounted regular price
                booking.total_amount = combo_price + discounted_regular_price
                booking.save()
        
        response_data = {
            'success': True, 
            'status': status,
            'status_display': dict(Stall.STATUS_CHOICES).get(status, status)
        }
    
    else:
        response_data = {
            'success': True, 
            'status': status,
            'status_display': dict(Stall.STATUS_CHOICES).get(status, status)
        }
    
    return JsonResponse(response_data)

def admin_booking(request):
    bookings_list = Booking.objects.all().order_by('-booking_date')
    paginator = Paginator(bookings_list, 10)  
    page = request.GET.get('page', 1)
    bookings = paginator.get_page(page)
    return render(request, 'home/transactions.html', {'bookings': bookings})

@require_POST
def admin_delete_booking(request, booking_id):
    """
    Delete a booking and free up the stalls
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Free up all stalls in this booking
    stalls = booking.stalls.all()
    stalls.update(status='available')
    
    # Delete the booking
    booking.delete()
    
    return JsonResponse({'success': True})