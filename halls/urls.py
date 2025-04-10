# halls/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('halls/create/', views.create_hall, name='create_hall'),
    path('halls/<int:hall_id>/', views.hall_detail, name='hall_detail'),
    path('halls/<int:hall_id>/create-stall/', views.create_stall, name='create_stall'),
    path('halls/<int:hall_id>/data/', views.get_hall_data, name='get_hall_data'),
    path('halls/<int:hall_id>/stall/<int:stall_id>/delete/', views.delete_stall, name='delete_stall'),
]
