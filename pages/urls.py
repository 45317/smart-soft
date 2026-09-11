from django.urls import path
from django_rag.urls import urlpatterns as rag_urlpatterns
from django.contrib.auth import views as auth_views
from . import views
urlpatterns = [
    # RAG urls
    *rag_urlpatterns,
###### Authentication
     path('', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=False
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
 #### Main pages   
    path('dashboard/', views.dashboard, name='dashboard'),
    path('hr/', views.hr, name='hr'),
    path('hr/add/', views.add_hr, name='add_hr'),
    path('hr/<int:pk>/edit/', views.edit_hr, name='edit_hr'),
    path('hr/<int:pk>/delete/', views.delete_hr, name='delete_hr'),
    path('crm/', views.crm, name='crm'),
    path('crm/add/', views.add_crm, name='add_crm'),
    path('crm/<int:pk>/edit/', views.edit_crm, name='edit_crm'),
    path('crm/<int:pk>/delete/', views.delete_crm, name='delete_crm'),
    path('products/', views.products, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),
 #### Tasks
    path('tasks/', views.tasks, name='tasks'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/<int:pk>/toggle/', views.toggle_task, name='toggle_task'),
 #### Attendance & Leave
    path('attendance/', views.attendance, name='attendance'),
    path('attendance/add/', views.add_attendance, name='add_attendance'),
    path('leaves/', views.leaves, name='leaves'),
    path('leaves/add/', views.add_leave, name='add_leave'),
 #### Export
    path('export/hr/', views.export_hr, name='export_hr'),
    path('export/crm/', views.export_crm, name='export_crm'),
    path('export/products/', views.export_products, name='export_products'),
 ]