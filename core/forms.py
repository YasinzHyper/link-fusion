from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import ShortenedURL, LinkGroup, Domain, QRCode, UserProfile


class ShortenURLForm(forms.ModelForm):
    class Meta:
        model = ShortenedURL
        fields = ['original_url', 'title', 'description']
        widgets = {
            'original_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter your URL here (e.g., https://example.com)'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Optional: Custom title for your link'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Optional: Description for your link',
                'rows': 3
            }),
        }
        labels = {
            'original_url': 'URL to shorten',
            'title': 'Custom Title (Optional)',
            'description': 'Description (Optional)',
        }

    def clean_original_url(self):
        url = self.cleaned_data['original_url']
        if not url.startswith(('http://', 'https://')):
            raise forms.ValidationError('URL must start with http:// or https://')
        return url


class LinkForm(forms.ModelForm):
    # Add QR code generation field
    generate_qr = forms.BooleanField(
        required=False,
        initial=False,
        label='Generate QR Code',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2'
        })
    )
    
    class Meta:
        model = ShortenedURL
        fields = [
            'original_url', 'title', 'description', 'domain', 
            'group', 'expires_at', 'max_clicks', 'password'
        ]
        widgets = {
            'original_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://example.com'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Custom title (optional)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Description (optional)'
            }),
            'domain': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'group': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'datetime-local'
            }),
            'max_clicks': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Maximum clicks (optional)'
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Password protection (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['group'].queryset = LinkGroup.objects.filter(user=user)
            self.fields['group'].empty_label = "No group"
        
        self.fields['domain'].queryset = Domain.objects.filter(is_active=True)
        self.fields['domain'].empty_label = "Default domain"

    def clean_original_url(self):
        url = self.cleaned_data['original_url']
        if not url.startswith(('http://', 'https://')):
            raise forms.ValidationError('URL must start with http:// or https://')
        return url
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle password hashing
        raw_password = self.cleaned_data.get('password')
        if raw_password:
            instance.set_password(raw_password)
        elif not self.instance.pk:  # New instance with no password
            instance.password = ''
        
        if commit:
            instance.save()
        return instance


class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'your-domain.com'
            }),
        }
        labels = {
            'name': 'Domain Name',
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        # Remove protocol if provided
        if name.startswith(('http://', 'https://')):
            name = name.split('://', 1)[1]
        # Remove trailing slash
        name = name.rstrip('/')
        # Basic domain validation
        if not name or '.' not in name:
            raise forms.ValidationError('Please enter a valid domain name (e.g., your-domain.com)')
        return name


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Your name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'your@email.com'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'rows': 6,
            'placeholder': 'Your message...'
        })
    )


class LinkGroupForm(forms.ModelForm):
    class Meta:
        model = LinkGroup
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Group description (optional)'
            }),
            'color': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'color'
            }),
        }


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Email address'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Last name'
            }),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class PasswordPromptForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Enter password to access this link',
            'autofocus': True
        }),
        label='Password',
        help_text='This link is password protected. Please enter the password to continue.'
    )


class QRCodeForm(forms.ModelForm):
    # Additional fields for QR code customization
    qr_content = forms.CharField(
        max_length=2048,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter URL or text to encode'
        }),
        label='URL or Text',
        help_text='The content to encode in the QR code'
    )
    
    format = forms.ChoiceField(
        choices=[
            ('png', 'PNG'),
            ('svg', 'SVG'),
            ('jpg', 'JPG'),
        ],
        initial='png',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )
    
    corner_style = forms.ChoiceField(
        choices=[
            ('square', 'Square'),
            ('rounded', 'Rounded'),
            ('circle', 'Circle'),
        ],
        initial='square',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )
    
    class Meta:
        model = QRCode
        fields = ['size', 'error_correction', 'fill_color', 'back_color']
        widgets = {
            'size': forms.Select(
                choices=[
                    (100, '100x100'),
                    (200, '200x200'),
                    (300, '300x300'),
                    (400, '400x400'),
                    (500, '500x500'),
                ],
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                }
            ),
            'error_correction': forms.Select(
                choices=[
                    ('L', 'Low (7%)'),
                    ('M', 'Medium (15%)'),
                    ('Q', 'Quartile (25%)'),
                    ('H', 'High (30%)'),
                ],
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                }
            ),
            'fill_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'w-16 h-10 border border-gray-300 rounded-lg'
            }),
            'back_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'w-16 h-10 border border-gray-300 rounded-lg'
            }),
        }


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'First Name'
        }),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Last Name'
        }),
        label='Last Name'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Email Address'
        }),
        label='Email Address'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class NotificationSettingsForm(forms.ModelForm):
    email_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
        label='Email Notifications'
    )
    performance_alerts = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
        label='Link Performance Alerts'
    )
    security_alerts = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
        label='Security Alerts'
    )
    weekly_reports = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
        label='Weekly Reports'
    )
    marketing_updates = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
        label='Marketing Updates'
    )

    class Meta:
        model = UserProfile
        fields = ['email_notifications', 'performance_alerts', 'security_alerts', 'weekly_reports', 'marketing_updates']


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Current Password'
        }),
        label='Current Password'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'New Password'
        }),
        label='New Password'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Confirm New Password'
        }),
        label='Confirm New Password'
    ) 