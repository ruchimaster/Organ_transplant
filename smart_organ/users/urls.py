from django.urls import path
from . import views

urlpatterns = [

    # Signup page
    path('', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("approve-match/<int:match_id>/", views.approve_match, name="approve_match"),
    path("notifications/", views.notifications_view, name="notifications"),
    path('login/', views.login_view, name='login'),
    path('hospital/match/', views.match_organs, name='match_organs'),
    path('hospital/urgent/', views.urgent_requests, name='urgent_requests'),
    path("tracking/<int:match_id>/", views.view_tracking, name="view_tracking"),
    path('hospital/match-history/', views.match_history, name='match_history'),
    #path("tracking/<int:match_id>/update/", views.update_tracking, name="update_tracking"),
    path('update-status/<int:donation_id>/', views.update_status, name='update_status'),
    #path('contact/<int:hospital_id>/', views.contact_hospital, name='contact_hospital'),
    #path('notifications/', views.notifications, name='notifications'),
    path('update-organ-status/', views.update_organ_status, name='update_organ_status'),
    path('contact-hospital/<int:hospital_id>/', views.contact_hospital, name='contact_hospital'),

]