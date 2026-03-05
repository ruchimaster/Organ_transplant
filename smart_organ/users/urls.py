from django.urls import path
from . import views

urlpatterns = [
    path('', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("notifications/", views.notifications_view, name="notifications"),
]