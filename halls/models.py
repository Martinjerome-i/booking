# halls/models.py
from django.db import models


class Hall(models.Model):
    name = models.CharField(max_length=100)
    length = models.IntegerField(help_text="Length in meters")
    breadth = models.IntegerField(help_text="Breadth in meters")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_area(self):
        return self.length * self.breadth


class Stall(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='stalls')
    stall_number = models.CharField(max_length=20)

    # These represent the top-left corner coordinates of the stall
    x_start = models.IntegerField()
    y_start = models.IntegerField()

    # These represent the width and height of the stall in grid units
    width = models.IntegerField()
    height = models.IntegerField()

    # For storing actual selected boxes (helpful for irregular shapes)
    selected_boxes = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Stall {self.stall_number} - {self.hall.name}"

    @property
    def area(self):
        return len(self.selected_boxes)