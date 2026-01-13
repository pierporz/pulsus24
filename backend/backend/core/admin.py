from django.contrib import admin
from .models import Source, Keyword, Post

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("username", "enabled", "poll_interval_sec", "limit_items", "last_polled_at")
    list_filter = ("enabled",)
    search_fields = ("username",)

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("type", "pattern", "enabled", "match_field")
    list_filter = ("enabled", "type", "match_field")
    search_fields = ("pattern",)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "status", "flag_y", "sentiment", "pub_date", "wp_post_id")
    list_filter = ("status", "flag_y", "sentiment", "source")
    search_fields = ("link", "title", "description", "caption")
