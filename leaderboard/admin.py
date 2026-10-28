"""Leaderboard Admin"""
from django.contrib import admin
from django.utils.html import format_html
from .models import LeaderboardEntry, TeamLeaderboard


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ['rank_display', 'player', 'category', 'rank_points', 'total_wins', 'total_matches', 'win_rate', 'season']
    list_filter = ['category', 'season']
    search_fields = ['player__ign', 'player__user__email']
    ordering = ['rank']
    list_editable = ['rank_points', 'total_wins', 'total_matches']

    def rank_display(self, obj):
        icons = {1: '🥇', 2: '🥈', 3: '🥉'}
        icon = icons.get(obj.rank, f'#{obj.rank}')
        return format_html('<strong>{}</strong>', icon)
    rank_display.short_description = 'Rank'

    def win_rate(self, obj):
        return f"{obj.win_rate}%"
    win_rate.short_description = 'Win Rate'


@admin.register(TeamLeaderboard)
class TeamLeaderboardAdmin(admin.ModelAdmin):
    list_display = ['rank', 'team', 'category', 'rank_points', 'total_wins', 'total_matches', 'season']
    list_filter = ['category', 'season']
    ordering = ['rank']
