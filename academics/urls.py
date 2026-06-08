from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/<int:pk>/update/', views.session_update, name='session_update'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
    
    path('classes/', views.class_list, name='class_list'),
    path('classes/<int:pk>/delete/', views.class_delete, name='class_delete'),
    
    path('sections/', views.section_list, name='section_list'),
    path('sections/<int:pk>/delete/', views.section_delete, name='section_delete'),
    
    path('class-sections/', views.class_section_list, name='class_section_list'),
    path('class-sections/<int:pk>/delete/', views.class_section_delete, name='class_section_delete'),
    
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),
    
    path('promotion-wizard/', views.promotion_wizard, name='promotion_wizard'),
]
