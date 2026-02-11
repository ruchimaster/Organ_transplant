from django.urls import path
from . import views

urlpatterns = [
    path('', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

