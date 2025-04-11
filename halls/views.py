# halls/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Hall, Stall
import json


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
            selected_boxes=selected_boxes
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
        stall.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})