from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-restore/', views.backup_restore_view, name='backup_restore'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/students/excel/', views.export_students_excel, name='export_students_excel'),
    path('reports/collections/excel/', views.export_collections_excel, name='export_collections_excel'),
]
