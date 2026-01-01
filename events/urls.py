
# events/urls.py
from django.urls import path
from . import views
from . import auth_views

urlpatterns = [
    # Public pages
    path('', views.event_list, name='event_list'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('ticket/<uuid:ticket_id>/', views.ticket_confirmation, name='ticket_confirmation'),
    
    # Admin authentication
    path('admin/login/', auth_views.admin_login, name='admin_login'),
    path('admin/logout/', auth_views.admin_logout, name='admin_logout'),
    
    # Admin-only pages (protected)
    path('scan/', views.scan_qr, name='scan_qr'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Optional: User registration
    path('register/', auth_views.user_register, name='user_register'),
]