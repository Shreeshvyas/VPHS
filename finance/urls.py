from django.urls import path
from . import views

urlpatterns = [
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/approve/', views.expense_approve, name='expense_approve'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    
    path('incomes/', views.income_list, name='income_list'),
    path('incomes/create/', views.income_create, name='income_create'),
    
    path('daybook/', views.daybook, name='daybook'),
    path('cashbook/', views.cashbook_ledger, name='cashbook'),
]
