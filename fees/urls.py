from django.urls import path
from . import views

urlpatterns = [
    path('fee-types/', views.fee_type_list, name='fee_type_list'),
    path('fee-types/<int:pk>/delete/', views.fee_type_delete, name='fee_type_delete'),
    
    path('class-fees/', views.class_fee_list, name='class_fee_list'),
    path('class-fees/<int:pk>/delete/', views.class_fee_delete, name='class_fee_delete'),
    
    path('discounts/', views.student_discount_list, name='student_discount_list'),
    
    path('collect/', views.fee_collection_dashboard, name='fee_collection_dashboard'),
    path('collect/<int:enrollment_id>/process/', views.collect_fee, name='collect_fee'),
    
    path('receipts/', views.receipt_history, name='receipt_history'),
    path('receipts/<int:receipt_id>/download/', views.download_receipt_pdf, name='download_receipt'),
    
    path('dues/', views.due_report, name='due_report'),
    path('dues/<int:enrollment_id>/remind/', views.send_due_reminder, name='send_due_reminder'),
]
