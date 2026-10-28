"""
Tournaments Admin
Fixed: removed junk class stub, corrected RegistrationAdmin to use real model fields only.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Tournament, Registration


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'game', 'mode', 'status', 'entry_fee_display',
        'registered_count', 'max_players', 'fill_bar',
        'registration_deadline', 'is_featured'
    ]
    list_filter  = ['game', 'mode', 'status', 'is_featured', 'is_active']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-created_at']
    list_editable = ['status', 'is_featured']
    date_hierarchy = 'start_date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'game', 'mode', 'description', 'rules', 'banner')
        }),
        ('Registration', {
            'fields': ('entry_fee', 'max_players', 'registration_deadline')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'match_time')
        }),
        ('Prize Pool', {
            'fields': ('prize_pool', 'first_prize', 'second_prize', 'third_prize')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'is_featured')
        }),
    )

    def entry_fee_display(self, obj):
        if obj.entry_fee == 0:
            return format_html('<span style="color:green;">FREE</span>')
        return f'₹{obj.entry_fee}'
    entry_fee_display.short_description = 'Entry Fee'

    def registered_count(self, obj):
        return obj.registrations.filter(status='CONFIRMED').count()
    registered_count.short_description = 'Registered'

    def fill_bar(self, obj):
        pct = obj.fill_percentage
        color = '#00F5FF' if pct < 80 else '#C41212'
        return format_html(
            '<div style="width:100px;background:#333;border-radius:3px;">'
            '<div style="width:{}%;background:{};height:8px;border-radius:3px;"></div>'
            '</div> {}%',
            pct, color, pct
        )
    fill_bar.short_description = 'Slots'

    actions = ['open_registration', 'close_registration', 'set_ongoing', 'set_completed']

    def open_registration(self, request, queryset):
        queryset.update(status='REGISTRATION_OPEN')
    open_registration.short_description = '🟢 Open Registration'

    def close_registration(self, request, queryset):
        queryset.update(status='REGISTRATION_CLOSED')
    close_registration.short_description = '🔴 Close Registration'

    def set_ongoing(self, request, queryset):
        queryset.update(status='ONGOING')
    set_ongoing.short_description = '⚔️ Set Ongoing'

    def set_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
    set_completed.short_description = '🏆 Set Completed'


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'player', 'tournament', 'payment_method',
        'payment_status', 'status', 'transaction_id', 'registered_at',
    ]
    list_filter  = ['status', 'payment_method', 'payment_status', 'tournament__game']
    search_fields = [
        'player__ign', 'player__user__email',
        'player__ign', 'player__user__email', 'tournament__title', 'transaction_id'
    ]
    ordering = ['-registered_at']
    list_editable = ['status']

    actions = ['confirm_registrations', 'cancel_registrations', 'verify_upi_payments']

    def confirm_registrations(self, request, queryset):
        for reg in queryset:
            reg.confirm()
        self.message_user(request, f'{queryset.count()} registration(s) confirmed.')
    confirm_registrations.short_description = '✅ Confirm Registrations'

    def cancel_registrations(self, request, queryset):
        queryset.update(status='CANCELLED')
        self.message_user(request, f'{queryset.count()} registration(s) cancelled.')
    cancel_registrations.short_description = '❌ Cancel Registrations'

    def verify_upi_payments(self, request, queryset):
        """Manually verify UPI payments and confirm registrations."""
        count = 0
        for reg in queryset:
            if reg.payment_method == 'UPI' and reg.payment_status != 'SUCCESS':
                reg.payment_status = 'SUCCESS'
                reg.confirm()
                count += 1
        self.message_user(request, f'{count} UPI payment(s) verified and registrations confirmed.')
    verify_upi_payments.short_description = '💰 Verify UPI Payments'
