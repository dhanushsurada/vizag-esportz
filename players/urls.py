"""Players URLs"""
from django.urls import path
from . import views

app_name = 'players'

urlpatterns = [
    path('', views.player_list, name='player_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create-profile/', views.create_profile, name='create_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('<int:player_id>/', views.player_profile, name='player_profile'),
]
