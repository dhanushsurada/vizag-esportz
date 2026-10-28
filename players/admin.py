"""Players Admin"""
from django.contrib import admin
from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['ign', 'primary_game', 'tier', 'rank_points', 'total_wins', 'total_matches']
    list_filter = ['primary_game', 'tier', 'is_available']
    search_fields = ['ign', 'game_id', 'user__first_name', 'user__email']
    ordering = ['-rank_points']
    readonly_fields = ['kd_ratio', 'win_rate', 'created_at', 'updated_at']

    actions = ['award_rank_points']

    def award_rank_points(self, request, queryset):
        for player in queryset:
            player.rank_points += 50
            player.update_tier()
        self.message_user(request, f'Awarded 50 rank points to {queryset.count()} player(s).')
    award_rank_points.short_description = 'Award 50 rank points'
