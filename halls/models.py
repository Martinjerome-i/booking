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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    
    @property
    def area(self):
        return self.width * self.height

    def __str__(self):
        return f"Stall {self.stall_number} in {self.hall.name}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
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
    
    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            # Use timestamp to create unique reference
            import random
            import string
            timestamp = timezone.now().strftime('%Y%m%d%H%M')
            random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.booking_reference = f"BK-{timestamp}-{random_string}"
        
        super().save(*args, **kwargs)
        
        # Update stall status immediately
        if self.status == 'booked':
            self.stalls.all().update(status='booked')
        elif self.status == 'cancelled':
            self.stalls.all().update(status='available')
    
    def __str__(self):
        return f"Booking {self.booking_reference} - {self.customer_name}"
    

class ComboStall(models.Model):
    name = models.CharField(max_length=100)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='combos')
    stalls = models.ManyToManyField(Stall, related_name='combos')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                               help_text="Optional custom price for the combo. If not set, will use sum of stall prices.")
    
    def __str__(self):
        return f"{self.name} - {self.hall.name}"
    
    @property
    def stall_count(self):
        return self.stalls.count()
    
    @property
    def total_price(self):
        if self.price:
            return self.price
        return sum(stall.price for stall in self.stalls.all())