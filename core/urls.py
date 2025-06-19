from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'core'

urlpatterns = [
    # Landing & Marketing Pages
    path('', views.IndexView.as_view(), name='index'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('features/', views.FeaturesView.as_view(), name='features'),
    path('pricing/', views.PricingView.as_view(), name='pricing'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('terms/', views.TermsOfServiceView.as_view(), name='terms'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy'),
    
    # Dashboard URLs (protected)
    path('dashboard/', login_required(views.DashboardView.as_view()), name='dashboard'),
    path('dashboard/create/', login_required(views.CreateLinkView.as_view()), name='create_link'),
    path('dashboard/links/', login_required(views.MyLinksView.as_view()), name='my_links'),
    path('dashboard/links/<int:pk>/edit/', login_required(views.EditLinkView.as_view()), name='edit_link'),
    path('dashboard/analytics/', login_required(views.AnalyticsView.as_view()), name='analytics'),
    path('dashboard/qr-codes/', login_required(views.QRCodesView.as_view()), name='qr_codes'),
    path('dashboard/settings/', login_required(views.SettingsView.as_view()), name='settings'),
    
    # Admin URLs (staff required)
    path('admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/users/', views.AdminUsersView.as_view(), name='admin_users'),
    path('admin/users/<int:user_id>/suspend/', views.AdminUserSuspendView.as_view(), name='admin_user_suspend'),
    path('admin/users/<int:user_id>/activate/', views.AdminUserActivateView.as_view(), name='admin_user_activate'),
    path('admin/users/<int:user_id>/delete/', views.AdminUserDeleteView.as_view(), name='admin_user_delete'),
    path('admin/links/', views.AdminLinksView.as_view(), name='admin_links'),
    path('admin/domains/', views.AdminDomainsView.as_view(), name='admin_domains'),
    
    # API endpoints for AJAX requests
    path('api/shorten/', views.ShortenURLView.as_view(), name='api_shorten'),
    path('api/links/<int:pk>/delete/', views.DeleteLinkView.as_view(), name='api_delete_link'),
    path('api/links/<int:pk>/toggle/', views.ToggleLinkView.as_view(), name='api_toggle_link'),
    
    path('api/links/<int:link_id>/toggle/', views.LinkToggleAPIView.as_view(), name='api_link_toggle'),
    path('api/links/<int:link_id>/delete/', views.LinkDeleteAPIView.as_view(), name='api_link_delete'),
    path('api/links/<int:link_id>/generate-qr/', views.GenerateQRCodeAPIView.as_view(), name='api_generate_qr'),
    path('api/qr-codes/<int:qr_id>/delete/', views.QRCodeDeleteAPIView.as_view(), name='api_qr_delete'),
    path('api/admin/domains/<int:domain_id>/toggle/', views.AdminDomainToggleAPIView.as_view(), name='api_admin_domain_toggle'),
    path('api/admin/domains/<int:domain_id>/delete/', views.AdminDomainDeleteAPIView.as_view(), name='api_admin_domain_delete'),
    
    # Password prompt for protected links
    path('password/<str:short_code>/', views.PasswordPromptView.as_view(), name='password_prompt'),
    
    # Short URL redirect (should be last to catch all remaining patterns)
    path('<str:short_code>/', views.RedirectView.as_view(), name='redirect'),
] 