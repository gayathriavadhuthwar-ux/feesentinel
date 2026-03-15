from . import views
from django.urls import path

urlpatterns = [
    path('', views.home, name='home'),
    path('student-auth/', views.student_auth, name='student_auth'),
    path('admin-auth/', views.admin_auth, name='admin_auth'),
    path('register/', views.register, name='register'),
    path('admin-register/', views.admin_register, name='admin_register'),
    path('login/', views.student_login, name='student_login'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('submit/', views.submit_receipt, name='submit_receipt'),
    path('my-receipts/', views.student_receipts, name='student_receipts'),
    path('receipt/<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/', views.admin_receipts, name='admin_receipts'),
    path('receipts/export_csv/', views.export_receipts_csv, name='export_receipts_csv'),
]