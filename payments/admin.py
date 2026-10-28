"""Payments Admin"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['player', 'tournament', 'amount_display', 'status_badge',
                    'razorpay_payment_id', 'created_at']
    list_filter = ['status', 'tournament__game']
    search_fields = ['player__ign',
                     'razorpay_order_id', 'retry_count', 'failure_reason', 'razorpay_payment_id']
    ordering = ['-created_at']
    readonly_fields = ['razorpay_order_id', 'retry_count', 'failure_reason', 'razorpay_payment_id',
                       'razorpay_signature', 'receipt', 'created_at', 'updated_at']

    def amount_display(self, obj):
        return f'₹{obj.amount_inr}'
    amount_display.short_description = 'Amount'

    def status_badge(self, obj):
        colors = {
            'SUCCESS': '#00C851',
            'PENDING': '#FFBB33',
            'FAILED': '#FF4444',
            'REFUNDED': '#00B0FF',
        }
        color = colors.get(obj.status, '#888')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'

    actions = ['mark_success', 'mark_failed', 'initiate_refund']

    def mark_success(self, request, queryset):
        queryset.update(status='SUCCESS')
        self.message_user(request, f'{queryset.count()} payment(s) marked as successful.')
    mark_success.short_description = '✅ Mark as Successful'

    def mark_failed(self, request, queryset):
        queryset.update(status='FAILED')
        self.message_user(request, f'{queryset.count()} payment(s) marked as failed.')
    mark_failed.short_description = '❌ Mark as Failed'

    def initiate_refund(self, request, queryset):
        queryset.update(status='REFUNDED')
        self.message_user(request, f'{queryset.count()} payment(s) marked for refund. Process via Razorpay dashboard.')
    initiate_refund.short_description = '↩️ Mark as Refunded'
