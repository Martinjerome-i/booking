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
    ]

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='stalls')
    stall_number = models.CharField(max_length=20)
    x_start = models.IntegerField()
    y_start = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    selected_boxes = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    @property
    def area(self):
        return self.width * self.height

    def __str__(self):
        return f"Stall {self.stall_number} in {self.hall.name}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, related_name='bookings')
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    booking_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    payment_status = models.BooleanField(default=False)
    booking_reference = models.CharField(max_length=20, unique=True)
    
    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            # Use timestamp to create unique reference
            import random
            import string
            timestamp = timezone.now().strftime('%Y%m%d%H%M')
            random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.booking_reference = f"BK-{timestamp}-{random_string}"
            
        # Update stall status when booking is created or updated
        if self.status == 'confirmed':
            self.stall.status = 'booked'
        elif self.status == 'cancelled':
            self.stall.status = 'available'
        self.stall.save()
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Booking {self.booking_reference} - {self.customer_name}"