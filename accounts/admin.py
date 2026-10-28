"""
Accounts - Admin Configuration
Role system: SuperAdmin (is_superuser) > Moderator (is_staff) > User
FIXED: Removed duplicate methods, broken standalone functions, duplicate actions list.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.contrib.auth.models import Group
from .models import NSRITUser, EmailVerificationToken, PasswordResetToken, AdminAccessLog


@admin.register(NSRITUser)
class NSRITUserAdmin(UserAdmin):

    list_display = [
        'get_full_name', 'email',
        'role_display', 'email_verified_badge', 'is_verified',
        'account_lock_status', 'date_joined'
    ]
    list_filter = ['is_verified', 'email_verified', 'is_active', 'is_staff']
    search_fields = ['first_name', 'last_name', 'email']
    ordering = ['-date_joined']

    actions = [
        'verify_users', 'unverify_users', 'verify_emails', 'unlock_accounts',
        'make_moderator', 'remove_moderator', 'make_superadmin', 'remove_admin_access',
    ]

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Verification', {'fields': ('email_verified', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Login Security', {'fields': ('failed_login_attempts', 'last_failed_login', 'account_locked_until')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'first_name', 'last_name', 'password1', 'password2')}),
    )
    readonly_fields = ['date_joined', 'last_login', 'last_failed_login']

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_staff

    def get_readonly_fields(self, request, obj=None):
        base = list(self.readonly_fields)
        if not request.user.is_superuser:
            base += ['is_staff', 'is_superuser', 'groups', 'user_permissions']
        return base

    def role_display(self, obj):
        if obj.is_superuser:
            return format_html('<span style="color:#FFD700;font-weight:bold;">👑 Super Admin</span>')
        elif obj.is_staff:
            return format_html('<span style="color:#00CED1;font-weight:bold;">🛡️ Moderator</span>')
        return format_html('<span style="color:#888;">👤 User</span>')
    role_display.short_description = 'Role'

    def email_verified_badge(self, obj):
        if obj.email_verified:
            return format_html('<span style="color:green;">✅ Verified</span>')
        return format_html('<span style="color:red;">❌ Unverified</span>')
    email_verified_badge.short_description = 'Email'

    def account_lock_status(self, obj):
        if obj.is_account_locked:
            return format_html('<span style="color:orange;">🔒 Locked</span>')
        if obj.failed_login_attempts >= 3:
            return format_html('<span style="color:orange;">⚠️ {} fails</span>', obj.failed_login_attempts)
        return format_html('<span style="color:green;">✅ OK</span>')
    account_lock_status.short_description = 'Login Status'

    def verify_users(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f'{queryset.count()} user(s) admin-verified.')
    verify_users.short_description = '✅ Admin-verify selected users'

    def unverify_users(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f'{queryset.count()} user(s) unverified.')
    unverify_users.short_description = '❌ Remove admin-verification'

    def verify_emails(self, request, queryset):
        queryset.update(email_verified=True)
        self.message_user(request, f'{queryset.count()} email(s) marked as verified.')
    verify_emails.short_description = '📧 Mark emails as verified'

    def unlock_accounts(self, request, queryset):
        queryset.update(failed_login_attempts=0, account_locked_until=None)
        self.message_user(request, f'{queryset.count()} account(s) unlocked.')
    unlock_accounts.short_description = '🔓 Unlock selected accounts'

    def make_moderator(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Only superadmin can assign moderators.')
            return
        group, _ = Group.objects.get_or_create(name='Moderator')
        for user in queryset:
            user.is_staff = True
            user.is_superuser = False
            user.groups.add(group)
            user.save()
        self.message_user(request, f'{queryset.count()} user(s) promoted to Moderator.')
    make_moderator.short_description = '🛡️ Promote to Moderator'

    def remove_moderator(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Only superadmin can remove moderators.')
            return
        for user in queryset:
            user.is_staff = False
            user.groups.filter(name='Moderator').delete()
            user.save()
        self.message_user(request, f'{queryset.count()} moderator(s) removed.')
    remove_moderator.short_description = '❌ Remove Moderator'

    def make_superadmin(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Only superadmin can assign superadmin.')
            return
        for user in queryset:
            user.is_staff = True
            user.is_superuser = True
            user.save()
        self.message_user(request, f'{queryset.count()} user(s) made Super Admin.')
    make_superadmin.short_description = '👑 Make Super Admin'

    def remove_admin_access(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Only superadmin can remove admin access.')
            return
        for user in queryset:
            if user == request.user:
                continue
            user.is_staff = False
            user.is_superuser = False
            user.groups.clear()
            user.save()
        self.message_user(request, f'{queryset.count()} user(s) admin access removed.')
    remove_admin_access.short_description = '🚫 Remove Admin Access'


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_short', 'created_at', 'expires_at', 'is_used', 'validity_badge']
    list_filter = ['is_used']
    search_fields = ['user__email']
    readonly_fields = ['token', 'created_at']
    ordering = ['-created_at']

    def token_short(self, obj):
        return str(obj.token)[:8] + '...'
    token_short.short_description = 'Token (short)'

    def validity_badge(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:green;">✅ Valid</span>')
        if obj.is_used:
            return format_html('<span style="color:gray;">✔ Used</span>')
        return format_html('<span style="color:red;">⏰ Expired</span>')
    validity_badge.short_description = 'Status'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_short', 'created_at', 'expires_at', 'is_used', 'ip_address', 'validity_badge']
    list_filter = ['is_used']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['token', 'created_at', 'ip_address']
    ordering = ['-created_at']

    def token_short(self, obj):
        return str(obj.token)[:8] + '...'
    token_short.short_description = 'Token (short)'

    def validity_badge(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:green;">✅ Valid</span>')
        if obj.is_used:
            return format_html('<span style="color:gray;">✔ Used</span>')
        return format_html('<span style="color:red;">⏰ Expired</span>')
    validity_badge.short_description = 'Status'


@admin.register(AdminAccessLog)
class AdminAccessLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action_badge', 'ip_address', 'path', 'notes']
    list_filter = ['action']
    search_fields = ['user__email', 'ip_address', 'path']
    readonly_fields = ['user', 'action', 'ip_address', 'path', 'timestamp', 'notes']
    ordering = ['-timestamp']

    def action_badge(self, obj):
        colors = {'ACCESS': 'green', 'DENIED': 'red', 'LOGIN': 'blue', 'LOGOUT': 'gray'}
        color = colors.get(obj.action, 'gray')
        return format_html('<span style="color:{};">{}</span>', color, obj.get_action_display())
    action_badge.short_description = 'Action'

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
