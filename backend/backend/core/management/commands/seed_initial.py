import os

from django.core.management.base import BaseCommand

from core.models import Keyword, Source


def _split_list(value: str):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Command(BaseCommand):
    help = "Seed initial Source and Keyword records from env vars (idempotent)."

    def handle(self, *args, **options):
        sources_raw = os.getenv("SEED_SOURCES", "")
        include_raw = os.getenv("SEED_KEYWORDS_INCLUDE", "")
        exclude_raw = os.getenv("SEED_KEYWORDS_EXCLUDE", "")

        poll_interval = int(os.getenv("SEED_POLL_INTERVAL_SEC", "120"))
        limit_items = int(os.getenv("SEED_LIMIT_ITEMS", "10"))

        sources = _split_list(sources_raw)
        includes = _split_list(include_raw)
        excludes = _split_list(exclude_raw)

        created_sources = 0
        for username in sources:
            _, created = Source.objects.get_or_create(
                username=username,
                defaults={
                    "enabled": True,
                    "poll_interval_sec": poll_interval,
                    "limit_items": limit_items,
                },
            )
            if created:
                created_sources += 1

        created_keywords = 0
        for pattern in includes:
            _, created = Keyword.objects.get_or_create(
                pattern=pattern,
                type=Keyword.INCLUDE,
                match_field=Keyword.BOTH,
                defaults={"enabled": True},
            )
            if created:
                created_keywords += 1

        for pattern in excludes:
            _, created = Keyword.objects.get_or_create(
                pattern=pattern,
                type=Keyword.EXCLUDE,
                match_field=Keyword.BOTH,
                defaults={"enabled": True},
            )
            if created:
                created_keywords += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seeded sources={created_sources} keywords={created_keywords}"
            )
        )
