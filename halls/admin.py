# halls/admin.py
from django.contrib import admin
from .models import Hall, Stall


class StallInline(admin.TabularInline):
    model = Stall
    extra = 0


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'length', 'breadth', 'total_area', 'stall_count')
    inlines = [StallInline]

    def stall_count(self, obj):
        return obj.stalls.count()

    stall_count.short_description = 'Number of Stalls'


@admin.register(Stall)
class StallAdmin(admin.ModelAdmin):
    list_display = ('stall_number', 'hall', 'area', 'x_start', 'y_start', 'width', 'height')
    list_filter = ('hall',)
    search_fields = ('stall_number', 'hall__name')