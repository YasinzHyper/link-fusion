from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from datetime import datetime, timedelta
import json

from django.contrib.auth.models import User
from .models import ShortenedURL, Click, QRCode, Domain, UserProfile, LinkGroup
from .forms import (
    ShortenURLForm, ContactForm, LinkForm, DomainForm, PasswordPromptForm, 
    QRCodeForm, UserProfileForm, NotificationSettingsForm, CustomPasswordChangeForm
)


# Landing & Marketing Pages
class IndexView(TemplateView):
    template_name = 'core/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ShortenURLForm()
        context['available_domains'] = Domain.objects.filter(is_active=True)
        return context


class AboutView(TemplateView):
    template_name = 'core/about.html'


class FeaturesView(TemplateView):
    template_name = 'core/features.html'


class PricingView(TemplateView):
    template_name = 'core/pricing.html'


class ContactView(TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ContactForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            # Handle contact form submission
            messages.success(request, 'Thank you for your message! We\'ll get back to you soon.')
            return redirect('contact')
        return self.render_to_response({'form': form})


class TermsOfServiceView(TemplateView):
    template_name = 'core/terms.html'


class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy.html'


# Authentication Views moved to users app


# Dashboard Views
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's links and stats
        user_links = ShortenedURL.objects.filter(user=user)
        total_links = user_links.count()
        total_clicks = sum(link.clicks for link in user_links)
        recent_links = user_links[:5]
        
        # Get recent clicks for analytics
        recent_clicks = Click.objects.filter(
            url__user=user
        ).order_by('-clicked_at')[:10]
        
        context.update({
            'total_links': total_links,
            'total_clicks': total_clicks,
            'recent_links': recent_links,
            'recent_clicks': recent_clicks,
        })
        return context


class CreateLinkView(LoginRequiredMixin, CreateView):
    model = ShortenedURL
    form_class = LinkForm
    template_name = 'core/dashboard/create_link.html'
    success_url = reverse_lazy('core:my_links')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_domains'] = Domain.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # Generate QR code if requested
        if form.cleaned_data.get('generate_qr'):
            qr_code = QRCode.objects.create(url=self.object)
            qr_code.generate_qr_code(self.request)
            qr_code.save()
            messages.success(self.request, 'Link created successfully with QR code!')
        else:
            messages.success(self.request, 'Link created successfully!')
            
        return response


class MyLinksView(LoginRequiredMixin, ListView):
    model = ShortenedURL
    template_name = 'core/dashboard/my_links.html'
    context_object_name = 'links'
    paginate_by = 20
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = ShortenedURL.objects.filter(user=self.request.user).select_related('domain')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(original_url__icontains=search) |
                Q(short_code__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'expired':
            from django.utils import timezone
            queryset = queryset.filter(expires_at__lt=timezone.now())
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's link statistics
        user_links = ShortenedURL.objects.filter(user=user)
        total_links = user_links.count()
        active_links = user_links.filter(is_active=True).count()
        total_clicks = sum(link.clicks for link in user_links)
        
        # Calculate CTR (Click Through Rate)
        avg_ctr = (total_clicks / total_links * 100) if total_links > 0 else 0
        
        # Add search and filter parameters
        from django.utils import timezone
        context.update({
            'total_links': total_links,
            'active_links': active_links,
            'total_clicks': total_clicks,
            'avg_ctr': round(avg_ctr, 1),
            'search': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'now': timezone.now(),
        })
        
        return context


class EditLinkView(LoginRequiredMixin, UpdateView):
    model = ShortenedURL
    form_class = LinkForm
    template_name = 'core/dashboard/edit_link.html'
    success_url = reverse_lazy('core:my_links')
    
    def get_queryset(self):
        return ShortenedURL.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Link updated successfully!')
        return response


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's data
        user_links = ShortenedURL.objects.filter(user=user)
        all_clicks = Click.objects.filter(url__user=user)
        
        # Current period (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        sixty_days_ago = datetime.now() - timedelta(days=60)
        
        current_clicks = all_clicks.filter(clicked_at__gte=thirty_days_ago)
        previous_clicks = all_clicks.filter(clicked_at__gte=sixty_days_ago, clicked_at__lt=thirty_days_ago)
        
        # Calculate totals and percentages
        total_clicks = all_clicks.count()
        current_period_clicks = current_clicks.count()
        previous_period_clicks = previous_clicks.count()
        
        # Calculate percentage changes
        def calculate_percentage_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)
        
        clicks_change = calculate_percentage_change(current_period_clicks, previous_period_clicks)
        
        # Unique visitors (unique IP addresses)
        current_unique_visitors = current_clicks.values('ip_address').distinct().count()
        previous_unique_visitors = previous_clicks.values('ip_address').distinct().count()
        unique_visitors_change = calculate_percentage_change(current_unique_visitors, previous_unique_visitors)
        
        # Click rate (clicks per link)
        total_links = user_links.count()
        avg_click_rate = round((total_clicks / total_links * 100), 1) if total_links > 0 else 0
        current_avg_rate = round((current_period_clicks / total_links * 100), 1) if total_links > 0 else 0
        previous_avg_rate = round((previous_period_clicks / total_links * 100), 1) if total_links > 0 else 0
        click_rate_change = calculate_percentage_change(current_avg_rate, previous_avg_rate)
        
        # Average daily clicks
        avg_daily_clicks = round(current_period_clicks / 30, 0) if current_period_clicks > 0 else 0
        prev_avg_daily = round(previous_period_clicks / 30, 0) if previous_period_clicks > 0 else 0
        daily_clicks_change = calculate_percentage_change(avg_daily_clicks, prev_avg_daily)
        
        # Top performing links
        top_links = user_links.filter(clicks__gt=0).order_by('-clicks')[:5]
        
        # Recent activity (last 10 clicks)
        recent_activity = all_clicks.select_related('url').order_by('-clicked_at')[:10]
        
        # Geographic data
        countries = all_clicks.exclude(country='').values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        total_geo_clicks = sum(c['count'] for c in countries)
        
        # Add percentages to countries
        for country in countries:
            country['percentage'] = round((country['count'] / total_geo_clicks * 100), 1) if total_geo_clicks > 0 else 0
        
        # Device types
        devices = all_clicks.exclude(device_type='').values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        total_device_clicks = sum(d['count'] for d in devices)
        for device in devices:
            device['percentage'] = round((device['count'] / total_device_clicks * 100), 1) if total_device_clicks > 0 else 0
        
        # Browser data
        browsers = all_clicks.exclude(browser='').values('browser').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        total_browser_clicks = sum(b['count'] for b in browsers)
        for browser in browsers:
            browser['percentage'] = round((browser['count'] / total_browser_clicks * 100), 1) if total_browser_clicks > 0 else 0
        
        # Referrer data
        referrers = all_clicks.exclude(referer='').values('referer').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Add direct traffic
        direct_traffic = all_clicks.filter(referer='').count()
        
        total_referrer_clicks = sum(r['count'] for r in referrers) + direct_traffic
        for referrer in referrers:
            referrer['percentage'] = round((referrer['count'] / total_referrer_clicks * 100), 1) if total_referrer_clicks > 0 else 0
        
        # Format referrer domain names
        import urllib.parse
        for referrer in referrers:
            try:
                parsed = urllib.parse.urlparse(referrer['referer'])
                referrer['domain'] = parsed.netloc.replace('www.', '') if parsed.netloc else referrer['referer']
            except:
                referrer['domain'] = referrer['referer']
        
        direct_percentage = round((direct_traffic / total_referrer_clicks * 100), 1) if total_referrer_clicks > 0 else 0
        
        context.update({
            # Overview stats
            'total_clicks': total_clicks,
            'clicks_change': clicks_change,
            'clicks_change_positive': clicks_change >= 0,
            
            'unique_visitors': all_clicks.values('ip_address').distinct().count(),
            'unique_visitors_change': unique_visitors_change,
            'unique_visitors_change_positive': unique_visitors_change >= 0,
            
            'click_rate': avg_click_rate,
            'click_rate_change': click_rate_change,
            'click_rate_change_positive': click_rate_change >= 0,
            
            'avg_daily_clicks': avg_daily_clicks,
            'daily_clicks_change': daily_clicks_change,
            'daily_clicks_change_positive': daily_clicks_change >= 0,
            
            # Data for tabs
            'top_links': top_links,
            'recent_activity': recent_activity,
            'countries': countries,
            'devices': devices,
            'browsers': browsers,
            'referrers': referrers,
            'direct_traffic': direct_traffic,
            'direct_percentage': direct_percentage,
            
            # Additional stats
            'total_links': total_links,
            'active_links': user_links.filter(is_active=True).count(),
        })
        return context


class QRCodesView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard/qr_codes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get QR codes for current user - exclude ones without images
        if self.request.user.is_staff:
            # Admin sees all QR codes
            qr_codes = QRCode.objects.select_related('url', 'url__user').exclude(image='').order_by('-created_at')
        else:
            # Regular users see only their QR codes
            qr_codes = QRCode.objects.filter(url__user=self.request.user).select_related('url').exclude(image='').order_by('-created_at')
        
        # Add QR form
        context['qr_form'] = QRCodeForm()
        context['qr_codes'] = qr_codes
        context['is_admin'] = self.request.user.is_staff
        
        # QR code statistics
        total_qr_codes = qr_codes.count()
        total_scans = sum(qr.get_scan_count() for qr in qr_codes)
        
        context.update({
            'total_qr_codes': total_qr_codes,
            'total_scans': total_scans,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        form = QRCodeForm(request.POST, request.FILES)
        
        if form.is_valid():
            qr_content = form.cleaned_data['qr_content']
            
            # Check if it's a URL that matches one of user's links
            shortened_url = None
            if qr_content.startswith(('http://', 'https://')):
                # Try to find matching shortened URL
                try:
                    # Extract short code from URL
                    import urllib.parse
                    parsed = urllib.parse.urlparse(qr_content)
                    short_code = parsed.path.strip('/')
                    
                    if short_code:
                        shortened_url = ShortenedURL.objects.filter(
                            user=request.user,
                            short_code=short_code
                        ).first()
                except:
                    pass
            
            # If no matching URL found, create a standalone QR code entry
            if not shortened_url:
                # Create a temporary ShortenedURL for standalone QR codes
                shortened_url = ShortenedURL.objects.create(
                    user=request.user,
                    original_url=qr_content if qr_content.startswith(('http://', 'https://')) else f'https://{qr_content}',
                    title=f'QR Code - {qr_content[:50]}{"..." if len(qr_content) > 50 else ""}',
                    is_active=True
                )
            
            # Create QR code
            qr_code = QRCode.objects.create(
                url=shortened_url,
                size=form.cleaned_data['size'],
                error_correction=form.cleaned_data['error_correction'],
                fill_color=form.cleaned_data['fill_color'],
                back_color=form.cleaned_data['back_color']
            )
            
            # Generate the QR code image
            qr_code.generate_qr_code(qr_content)
            
            messages.success(request, 'QR code generated successfully!')
            return redirect('core:qr_codes')
        
        # If form is invalid, return with errors
        context = self.get_context_data()
        context['qr_form'] = form
        return self.render_to_response(context)


class DomainsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard/domains.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Show message that domains are admin-only now
        context['admin_only_message'] = True
        context['available_domains'] = Domain.objects.filter(is_active=True)
        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Initialize forms with current user data
        context['profile_form'] = UserProfileForm(instance=self.request.user)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        context['notification_form'] = NotificationSettingsForm(instance=user_profile)
        context['password_form'] = CustomPasswordChangeForm(self.request.user)
        
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tab = request.POST.get('tab', 'profile')
        
        if tab == 'profile':
            form = UserProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('core:settings')
            else:
                context['profile_form'] = form
                messages.error(request, 'Please correct the errors below.')
        
        elif tab == 'notifications':
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            form = NotificationSettingsForm(request.POST, instance=user_profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Notification preferences updated successfully!')
                return redirect('core:settings')
            else:
                context['notification_form'] = form
                messages.error(request, 'Please correct the errors below.')
        
        elif tab == 'security':
            form = CustomPasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                # Keep user logged in after password change
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('core:settings')
            else:
                context['password_form'] = form
                messages.error(request, 'Please correct the errors below.')
        
        return self.render_to_response(context)


# Admin Views (Staff Required)
class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'core/admin/admin_dashboard.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Admin statistics
        total_users = UserProfile.objects.count()
        total_links = ShortenedURL.objects.count()
        total_clicks = Click.objects.count()
        active_links = ShortenedURL.objects.filter(is_active=True).count()
        
        context.update({
            'total_users': total_users,
            'total_links': total_links,
            'total_clicks': total_clicks,
            'active_links': active_links,
        })
        return context


class AdminUsersView(UserPassesTestMixin, ListView):
    model = User
    template_name = 'core/admin/users.html'
    context_object_name = 'users'
    paginate_by = 25
    ordering = ['-date_joined']
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        queryset = User.objects.select_related('userprofile').prefetch_related('shortenedurl_set')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'suspended':
            queryset = queryset.filter(is_active=False)
        
        # Filter by plan
        plan = self.request.GET.get('plan')
        if plan:
            queryset = queryset.filter(userprofile__plan=plan)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['plan_filter'] = self.request.GET.get('plan', '')
        
        # Add statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        suspended_users = User.objects.filter(is_active=False).count()
        
        context.update({
            'total_users': total_users,
            'active_users': active_users,
            'suspended_users': suspended_users,
        })
        
        return context


class AdminLinksView(UserPassesTestMixin, ListView):
    model = ShortenedURL
    template_name = 'core/admin/links.html'
    context_object_name = 'links'
    paginate_by = 50
    
    def test_func(self):
        return self.request.user.is_staff


class AdminDomainsView(UserPassesTestMixin, TemplateView):
    template_name = 'core/admin/domains.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get domains with link counts
        domains = Domain.objects.all().order_by('-created_at')
        
        # Add link count to each domain
        for domain in domains:
            domain.link_count = domain.get_link_count()
            domain.total_clicks = domain.get_total_clicks()
        
        context['domains'] = domains
        context['form'] = DomainForm()
        
        # Domain statistics
        context['total_domains'] = Domain.objects.count()
        context['active_domains'] = Domain.objects.filter(is_active=True).count()
        context['inactive_domains'] = Domain.objects.filter(is_active=False).count()
        
        return context
    
    def post(self, request, *args, **kwargs):
        form = DomainForm(request.POST)
        if form.is_valid():
            try:
                domain = form.save()
                messages.success(request, f'Domain "{domain.name}" has been added successfully!')
                return redirect('core:admin_domains')
            except Exception as e:
                messages.error(request, f'Error adding domain: {str(e)}')
        else:
            messages.error(request, 'Please check the form errors below.')
        
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class AdminPlansView(UserPassesTestMixin, TemplateView):
    template_name = 'core/admin/plans.html'
    
    def test_func(self):
        return self.request.user.is_staff


# Admin User Management AJAX Views
class AdminUserSuspendView(UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_staff
    
    def post(self, request, user_id, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Don't allow suspending superusers or staff
            if user.is_superuser or user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot suspend admin users'
                }, status=400)
            
            user.is_active = False
            user.save()
            
            messages.success(request, f'User {user.username} has been suspended.')
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class AdminUserActivateView(UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_staff
    
    def post(self, request, user_id, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=user_id)
            user.is_active = True
            user.save()
            
            messages.success(request, f'User {user.username} has been activated.')
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class AdminUserDeleteView(UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_staff
    
    def delete(self, request, user_id, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Don't allow deleting superusers, staff, or current user
            if user.is_superuser or user.is_staff or user == request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot delete admin users or yourself'
                }, status=400)
            
            username = user.username
            user.delete()
            
            messages.success(request, f'User {username} has been deleted.')
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


# API Views for AJAX requests
class ShortenURLView(TemplateView):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            original_url = data.get('url')
            domain_id = data.get('domain')
            
            if not original_url:
                return JsonResponse({'error': 'URL is required'}, status=400)
            
            # Get domain if specified
            domain = None
            if domain_id:
                try:
                    domain = Domain.objects.get(id=domain_id, is_active=True)
                except Domain.DoesNotExist:
                    return JsonResponse({'error': 'Invalid domain selected'}, status=400)
            
            # Create shortened URL
            shortened_url = ShortenedURL.objects.create(
                original_url=original_url,
                domain=domain,
                user=request.user if request.user.is_authenticated else None
            )
            
            return JsonResponse({
                'success': True,
                'short_url': shortened_url.get_short_url(request),
                'short_code': shortened_url.short_code
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class DeleteLinkView(LoginRequiredMixin, DeleteView):
    model = ShortenedURL
    
    def get_queryset(self):
        return ShortenedURL.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return JsonResponse({'success': True})


class ToggleLinkView(LoginRequiredMixin, TemplateView):
    def post(self, request, pk, *args, **kwargs):
        link = get_object_or_404(ShortenedURL, pk=pk, user=request.user)
        link.is_active = not link.is_active
        link.save()
        return JsonResponse({
            'success': True,
            'is_active': link.is_active
        })


# API Views for AJAX operations
@method_decorator(csrf_exempt, name='dispatch')
class LinkToggleAPIView(LoginRequiredMixin, TemplateView):
    def post(self, request, link_id, *args, **kwargs):
        try:
            link = get_object_or_404(ShortenedURL, id=link_id, user=request.user)
            link.is_active = not link.is_active
            link.save()
            
            return JsonResponse({
                'success': True,
                'is_active': link.is_active,
                'message': f'Link {"activated" if link.is_active else "deactivated"} successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class LinkDeleteAPIView(LoginRequiredMixin, TemplateView):
    def delete(self, request, link_id, *args, **kwargs):
        try:
            link = get_object_or_404(ShortenedURL, id=link_id, user=request.user)
            link_title = link.title or link.short_code
            link.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Link "{link_title}" deleted successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


# Redirect View for Short URLs
class RedirectView(TemplateView):
    def get(self, request, short_code, *args, **kwargs):
        try:
            url = get_object_or_404(ShortenedURL, short_code=short_code)
            
            if not url.can_be_accessed():
                return render(request, 'core/link_not_available.html', {
                    'message': 'This link is no longer available.'
                })
            
            # Check if password protection is required
            if url.has_password():
                # Check if password was already verified in this session
                session_key = f'password_verified_{short_code}'
                if not request.session.get(session_key, False):
                    # Redirect to password prompt
                    return HttpResponseRedirect(reverse('core:password_prompt', kwargs={'short_code': short_code}))
            
            # Track the click
            Click.objects.create(
                url=url,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER', ''),
            )
            
            # Update click count
            url.clicks += 1
            url.save()
            
            return HttpResponseRedirect(url.original_url)
            
        except ShortenedURL.DoesNotExist:
            return render(request, 'core/404.html', status=404)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordPromptView(TemplateView):
    template_name = 'core/password_prompt.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PasswordPromptForm()
        return context
    
    def post(self, request, short_code, *args, **kwargs):
        try:
            url = get_object_or_404(ShortenedURL, short_code=short_code)
            
            if not url.can_be_accessed():
                return render(request, 'core/link_not_available.html', {
                    'message': 'This link is no longer available.'
                })
            
            form = PasswordPromptForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data['password']
                
                if url.check_password(password):
                    # Password is correct, store in session and redirect
                    session_key = f'password_verified_{short_code}'
                    request.session[session_key] = True
                    request.session.set_expiry(3600)  # 1 hour
                    
                    return HttpResponseRedirect(reverse('core:redirect', kwargs={'short_code': short_code}))
                else:
                    # Password is incorrect
                    return render(request, self.template_name, {
                        'form': form,
                        'error_message': 'Incorrect password. Please try again.'
                    })
            
            return render(request, self.template_name, {
                'form': form
            })
            
        except ShortenedURL.DoesNotExist:
            return render(request, 'core/404.html', status=404)


@method_decorator(csrf_exempt, name='dispatch')
class GenerateQRCodeAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for generating QR codes via AJAX"""
    def post(self, request, link_id, *args, **kwargs):
        try:
            link = get_object_or_404(ShortenedURL, id=link_id, user=request.user)
            
            # Check if QR code already exists
            qr_code, created = QRCode.objects.get_or_create(url=link)
            
            if not qr_code.image:
                qr_code.generate_qr_code(request)
                qr_code.save()
            
            return JsonResponse({
                'success': True,
                'qr_url': qr_code.image.url if qr_code.image else None,
                'message': 'QR code generated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error generating QR code: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class QRCodeDeleteAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for deleting QR codes"""
    def delete(self, request, qr_id, *args, **kwargs):
        try:
            if request.user.is_staff:
                # Admin can delete any QR code
                qr_code = get_object_or_404(QRCode, id=qr_id)
            else:
                # Regular users can only delete their own QR codes
                qr_code = get_object_or_404(QRCode, id=qr_id, url__user=request.user)
            
            qr_code.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'QR code deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error deleting QR code: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class AdminDomainToggleAPIView(UserPassesTestMixin, TemplateView):
    """API endpoint for toggling domain status"""
    def test_func(self):
        return self.request.user.is_staff
    
    def post(self, request, domain_id, *args, **kwargs):
        try:
            domain = get_object_or_404(Domain, id=domain_id)
            domain.is_active = not domain.is_active
            domain.save()
            
            return JsonResponse({
                'success': True,
                'is_active': domain.is_active,
                'message': f'Domain "{domain.name}" {"activated" if domain.is_active else "deactivated"} successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error toggling domain: {str(e)}'
            })


@method_decorator(csrf_exempt, name='dispatch')
class AdminDomainDeleteAPIView(UserPassesTestMixin, TemplateView):
    """API endpoint for deleting domains"""
    def test_func(self):
        return self.request.user.is_staff
    
    def delete(self, request, domain_id, *args, **kwargs):
        try:
            domain = get_object_or_404(Domain, id=domain_id)
            
            # Check if domain has any links
            link_count = domain.get_link_count()
            if link_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot delete domain "{domain.name}". It has {link_count} associated links.'
                })
            
            domain_name = domain.name
            domain.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Domain "{domain_name}" deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error deleting domain: {str(e)}'
            })
