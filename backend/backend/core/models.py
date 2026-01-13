from django.db import models

class Source(models.Model):
    username = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)
    poll_interval_sec = models.IntegerField(default=120)
    limit_items = models.IntegerField(default=10)
    last_polled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username


class Keyword(models.Model):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    TYPE_CHOICES = [(INCLUDE, "Include"), (EXCLUDE, "Exclude")]

    TITLE = "title"
    DESCRIPTION = "description"
    BOTH = "both"
    FIELD_CHOICES = [(TITLE, "Title"), (DESCRIPTION, "Description"), (BOTH, "Both")]

    enabled = models.BooleanField(default=True)
    pattern = models.CharField(max_length=300)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=INCLUDE)
    match_field = models.CharField(max_length=12, choices=FIELD_CHOICES, default=BOTH)

    def __str__(self):
        return f"{self.type}: {self.pattern}"


class Post(models.Model):
    NEW = "NEW"
    SCANNED = "SCANNED"
    CAPTIONED = "CAPTIONED"
    PUBLISHED = "PUBLISHED"
    DROPPED = "DROPPED"
    STATUS_CHOICES = [
        (NEW, "New"),
        (SCANNED, "Scanned"),
        (CAPTIONED, "Captioned"),
        (PUBLISHED, "Published"),
        (DROPPED, "Dropped"),
    ]

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="posts")
    link = models.URLField(unique=True)
    pub_date = models.DateTimeField(null=True, blank=True)
    title = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")

    flag_y = models.BooleanField(null=True, blank=True)
    flag_reason = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=NEW)

    caption = models.CharField(max_length=200, blank=True, default="")
    sentiment = models.CharField(max_length=10, blank=True, default="")  # up/down/neutral
    ai_model = models.CharField(max_length=50, blank=True, default="")
    captioned_at = models.DateTimeField(null=True, blank=True)
    ai_error = models.TextField(blank=True, default="")

    wp_post_id = models.IntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    wp_status = models.CharField(max_length=10, blank=True, default="")
    wp_error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.link
