"""Moderator Dashboard URLs"""
from django.urls import path
from . import views

app_name = 'moderator'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('registrations/', views.registrations, name='registrations'),
    path('registrations/<int:reg_id>/approve/', views.approve_registration, name='approve_registration'),
    path('registrations/<int:reg_id>/reject/', views.reject_registration, name='reject_registration'),
    path('payments/', views.payments, name='payments'),
    path('payments/<int:payment_id>/success/', views.mark_payment_success, name='mark_payment_success'),
    path('payments/<int:payment_id>/fail/', views.mark_payment_failed, name='mark_payment_failed'),
    path('players/', views.players, name='players'),
    path('locked-accounts/', views.locked_accounts, name='locked_accounts'),
    path('locked-accounts/<int:user_id>/unlock/', views.unlock_account, name='unlock_account'),
]
