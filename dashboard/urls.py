from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.SiteListView.as_view(), name='dashboard_home'),

    # Sites
    path('sites/', views.SiteListView.as_view(), name='site_list'),
    path('sites/add/', views.SiteCreateView.as_view(), name='site_add'),
    path('sites/<int:pk>/edit/', views.SiteUpdateView.as_view(), name='site_edit'),
    path('sites/<int:pk>/delete/', views.SiteDeleteView.as_view(), name='site_delete'),

    # Commands
    path('commands/', views.CommandListView.as_view(), name='command_list'),
    path('commands/add/', views.CommandCreateView.as_view(), name='command_add'),
    path('commands/<int:pk>/edit/', views.CommandUpdateView.as_view(), name='command_edit'),
    path('commands/<int:pk>/delete/', views.CommandDeleteView.as_view(), name='command_delete'),
    path('commands/<int:pk>/start/', views.start_command_view, name='command_start'),
    path('commands/<int:pk>/stop/', views.stop_command_view, name='command_stop'),

    # Logs
    path('logs/', views.LogListView.as_view(), name='log_list'),
]
