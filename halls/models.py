# halls/models.py
from django.db import models
from django.utils import timezone


class Hall(models.Model):
    name = models.CharField(max_length=100)
    length = models.IntegerField(help_text="Length in meters")
    breadth = models.IntegerField(help_text="Breadth in meters")

    def __str__(self):
        return self.name

    @property
    def total_area(self):
        return self.length * self.breadth


class Stall(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('blocked', 'Blocked'), 
    ]
    
    # Add stall type choices
    TYPE_CHOICES = [
        ('eatery', 'Eatery'),
        ('non-eatery', 'Non-Eatery'),
    ]

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='stalls')
    stall_number = models.CharField(max_length=20)
    stall_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='eatery')
    x_start = models.IntegerField()
    y_start = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    selected_boxes = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=55000.00)
    
    @property
    def area(self):
        return self.width * self.height

    def __str__(self):
        return f"Stall {self.stall_number} in {self.hall.name}"


# Update the ComboStall model for the correct default price (₹1,30,000)
class ComboStall(models.Model):
    name = models.CharField(max_length=100)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='combos')
    stalls = models.ManyToManyField(Stall, related_name='combos')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=130000.00, 
                               help_text="Default price for combo stalls is ₹1,30,000")
    
    def __str__(self):
        return f"{self.name} - {self.hall.name}"
    
    @property
    def stall_count(self):
        return self.stalls.count()
    
    @property
    def total_price(self):
        # Always return the set price for combo stalls
        return self.price

    
class Booking(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('blocked', 'Blocked'), 
    ]
    
    stalls = models.ManyToManyField(Stall, related_name='bookings')
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    booking_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    notes = models.TextField(blank=True, null=True)
    payment_status = models.BooleanField(default=False)
    booking_reference = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_admin_booking = models.BooleanField(default=False)  # Added field to track admin bookings
    
    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            # Use timestamp to create unique reference
            import random
            import string
            timestamp = timezone.now().strftime('%Y%m%d%H%M')
            random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.booking_reference = f"IBFE-{timestamp}-{random_string}"
        
        super().save(*args, **kwargs)
        
        # Update stall status immediately based on booking status
        if self.status == 'booked':
            self.stalls.all().update(status='booked')
        elif self.status == 'cancelled':
            self.stalls.all().update(status='available')
        elif self.status == 'blocked':
            self.stalls.all().update(status='blocked')
    
    def __str__(self):
        return f"Booking {self.booking_reference} - {self.customer_name}"
    
class BookingCancellation(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='cancellations', null=True, blank=True)
    feedback = models.TextField()
    cancellation_date = models.DateTimeField(default=timezone.now)
    stall_ids = models.JSONField(default=list, help_text="Stores stall IDs if cancellation happens before booking is created")
    
    def __str__(self):
        if self.booking:
            return f"Cancellation for Booking {self.booking.booking_reference}"
        return f"Cancellation at {self.cancellation_date}"
    