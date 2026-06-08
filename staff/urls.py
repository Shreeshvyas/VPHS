from django.urls import path
from . import views

urlpatterns = [
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/', views.staff_profile, name='staff_profile'),
    path('staff/<int:pk>/update/', views.staff_update, name='staff_update'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),
    path('staff/<int:staff_id>/structure/', views.edit_salary_structure, name='edit_salary_structure'),
    
    path('salaries/', views.salary_dashboard, name='salary_dashboard'),
    path('salaries/<int:payment_id>/pay/', views.pay_salary, name='pay_salary'),
    path('salaries/<int:payment_id>/download/', views.download_payslip_pdf, name='download_payslip'),
]
