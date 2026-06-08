from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('create/', views.student_create, name='student_create'),
    path('<int:pk>/', views.student_profile, name='student_profile'),
    path('<int:pk>/update/', views.student_update, name='student_update'),
    path('<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('<int:pk>/id-card/', views.student_id_card_pdf, name='student_id_card'),
    path('api/search/', views.student_search_json, name='api_student_search'),
]
