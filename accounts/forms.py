"""
Accounts - Forms for Registration, Login, Password Reset, Email Verification
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRATION
# ──────────────────────────────────────────────────────────────────────────────

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Password (min 8 chars)',
            'id': 'id_password',
        }),
        min_length=8,
        help_text='Minimum 8 characters. Mix letters, numbers & symbols.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Confirm Password',
            'id': 'id_confirm_password',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control cyber-input',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control cyber-input',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control cyber-input',
                'placeholder': 'your@email.com',  # ── any email accepted
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control cyber-input',
                'placeholder': '10-digit mobile number',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password and confirm and password != confirm:
            raise forms.ValidationError({'confirm_password': 'Passwords do not match.'})
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.email_verified = True  # auto-verified (email confirmation disabled for launch)
        if commit:
            user.save()
        return user


# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────

class EsportzLoginForm(AuthenticationForm):
    # ── UPDATED: login by email instead of roll number
    username = forms.CharField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Your email address',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Password',
        })
    )


# ──────────────────────────────────────────────────────────────────────────────
# PROFILE UPDATE
# ──────────────────────────────────────────────────────────────────────────────

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control cyber-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control cyber-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-control cyber-input'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control cyber-input'}),
        }


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — REQUEST (step 1)
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Enter your email address',
            'autofocus': True,
        }),
        help_text='Enter the email address you registered with.'
    )

    def clean_email(self):
        value = self.cleaned_data['email'].lower().strip()
        # Try to find the user (but don't reveal if they exist — anti-enumeration)
        return value

    def get_user(self):
        value = self.cleaned_data.get('email', '').strip()
        User = get_user_model()
        return User.objects.filter(email__iexact=value, is_active=True).first()


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — SET NEW PASSWORD (step 2)
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(
        label='New Password',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'New Password (min 8 chars)',
            'autofocus': True,
            'id': 'id_new_password',
        }),
        help_text='Minimum 8 characters. Mix letters, numbers & symbols.',
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Confirm New Password',
            'id': 'id_confirm_password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('new_password')
        pw2 = cleaned_data.get('confirm_password')
        if pw1 and pw2 and pw1 != pw2:
            raise ValidationError({'confirm_password': 'Passwords do not match.'})
        return cleaned_data


# ──────────────────────────────────────────────────────────────────────────────
# RESEND VERIFICATION EMAIL
# ──────────────────────────────────────────────────────────────────────────────

class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control cyber-input',
            'placeholder': 'Your registered email address',
            'autofocus': True,
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        return email
