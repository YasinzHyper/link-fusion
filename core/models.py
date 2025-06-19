from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.hashers import make_password, check_password
from django.core.files.base import ContentFile
import string
import random
import qrcode
from io import BytesIO
from PIL import Image


def generate_short_code():
    """Generate a random short code for URLs"""
    length = 6
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


class Domain(models.Model):
    """Custom domains for branded short links"""
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_link_count(self):
        """Get the number of links using this domain"""
        return self.shortenedurl_set.count()
    
    def get_total_clicks(self):
        """Get total clicks for all links using this domain"""
        return sum(link.clicks for link in self.shortenedurl_set.all())
    
    def clean(self):
        """Validate domain name"""
        from django.core.exceptions import ValidationError
        import re
        
        # Remove protocol if present
        domain_name = self.name.replace('http://', '').replace('https://', '')
        
        # Basic domain validation
        domain_regex = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        )
        
        if not domain_regex.match(domain_name):
            raise ValidationError('Please enter a valid domain name (e.g., example.com)')
        
        self.name = domain_name


class UserProfile(models.Model):
    """Extended user profile for additional features"""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    links_created = models.PositiveIntegerField(default=0)
    clicks_received = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    performance_alerts = models.BooleanField(default=True)
    security_alerts = models.BooleanField(default=True)
    weekly_reports = models.BooleanField(default=False)
    marketing_updates = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan}"


class ShortenedURL(models.Model):
    """Main model for shortened URLs"""
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, default=generate_short_code)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    
    # User and domain relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    domain = models.ForeignKey(Domain, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Tracking and analytics
    clicks = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Advanced features
    password = models.CharField(max_length=255, blank=True, help_text="Password protection")
    max_clicks = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum allowed clicks")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.short_code} -> {self.original_url[:50]}"
    
    def get_short_url(self, request=None):
        """Get the full short URL"""
        if self.domain:
            domain = self.domain.name
        elif request:
            domain = request.get_host()
        else:
            # Fallback for when no request is available (like in templates)
            domain = 'localhost:8001'
        return f"https://{domain}/{self.short_code}"
    
    @property
    def short_url(self):
        """Property for easier template access"""
        return self.get_short_url()
    
    def is_expired(self):
        """Check if the link has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_be_accessed(self):
        """Check if the link can be accessed based on various conditions"""
        if not self.is_active:
            return False
        if self.is_expired():
            return False
        if self.max_clicks and self.clicks >= self.max_clicks:
            return False
        return True
    
    def has_password(self):
        """Check if the link is password protected"""
        return bool(self.password)
    
    def set_password(self, raw_password):
        """Set password with proper hashing"""
        if raw_password:
            self.password = make_password(raw_password)
        else:
            self.password = ''
    
    def check_password(self, raw_password):
        """Check if the provided password is correct"""
        if not self.password:
            return True  # No password set
        return check_password(raw_password, self.password)


class Click(models.Model):
    """Track clicks on shortened URLs"""
    url = models.ForeignKey(ShortenedURL, on_delete=models.CASCADE, related_name='click_records')
    
    # Request information
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    referer = models.URLField(blank=True)
    
    # Geographic information (can be populated via IP lookup)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Device information
    device_type = models.CharField(max_length=50, blank=True)  # mobile, desktop, tablet
    browser = models.CharField(max_length=100, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    
    # Timestamp
    clicked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-clicked_at']
    
    def __str__(self):
        return f"Click on {self.url.short_code} at {self.clicked_at}"
    
    def populate_analytics_data(self):
        """
        Populate device, browser, OS, and geographic data from user agent and IP
        """
        from .utils import parse_user_agent, get_location_from_ip
        
        # Parse user agent for device/browser/OS info
        if self.user_agent:
            ua_data = parse_user_agent(self.user_agent)
            self.device_type = ua_data['device_type']
            self.browser = ua_data['browser']
            self.operating_system = ua_data['operating_system']
        
        # Get geographic data from IP
        if self.ip_address:
            location_data = get_location_from_ip(self.ip_address)
            self.country = location_data['country']
            self.city = location_data['city']
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically populate analytics data
        """
        # Only populate on creation (not updates)
        if not self.pk:
            self.populate_analytics_data()
        
        super().save(*args, **kwargs)
    
    @property
    def country_flag(self):
        """Get flag emoji for the country"""
        from .utils import get_country_flag_emoji
        return get_country_flag_emoji(self.country)
    
    @property
    def browser_icon(self):
        """Get FontAwesome icon class for browser"""
        from .utils import get_browser_icon
        return get_browser_icon(self.browser)
    
    @property
    def device_icon(self):
        """Get FontAwesome icon class for device type"""
        from .utils import get_device_icon
        return get_device_icon(self.device_type)
    
    @property
    def os_icon(self):
        """Get FontAwesome icon class for operating system"""
        from .utils import get_os_icon
        return get_os_icon(self.operating_system)


class QRCode(models.Model):
    """QR codes for shortened URLs"""
    url = models.OneToOneField(ShortenedURL, on_delete=models.CASCADE, related_name='qr_code')
    
    # QR Code settings
    size = models.PositiveIntegerField(default=300)  # pixel size
    error_correction = models.CharField(max_length=1, default='M')  # L, M, Q, H
    
    # Style settings
    fill_color = models.CharField(max_length=7, default='#000000')  # hex color
    back_color = models.CharField(max_length=7, default='#FFFFFF')  # hex color
    
    # File storage
    image = models.ImageField(upload_to='qr_codes/', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"QR Code for {self.url.short_code}"
    
    def get_scan_count(self):
        """Get the number of times this QR code has been scanned (clicks on associated URL)"""
        return self.url.clicks
    
    def generate_qr_code(self, content=None, request=None):
        """Generate QR code image for the associated URL or custom content"""
        # Use custom content or get the full short URL
        if content:
            qr_content = content
        else:
            qr_content = self.url.get_short_url(request)
        
        # Set error correction level
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H,
        }
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(self.error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=10,
            border=4,
        )
        
        # Add data to QR code
        qr.add_data(qr_content)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color=self.fill_color, back_color=self.back_color)
        
        # Resize to desired size
        img = img.resize((self.size, self.size), Image.LANCZOS)
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Save to image field
        filename = f'qr_{self.url.short_code}.png'
        self.image.save(filename, ContentFile(buffer.getvalue()), save=True)
        
        return self.image


class LinkGroup(models.Model):
    """Organize links into groups/folders"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    color = models.CharField(max_length=7, default='#3B82F6')  # hex color
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['name', 'user']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


# Add link groups relationship to ShortenedURL
ShortenedURL.add_to_class('group', models.ForeignKey(LinkGroup, on_delete=models.SET_NULL, null=True, blank=True))
