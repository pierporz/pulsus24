import re
from django.core.management.base import BaseCommand
from core.models import Keyword, Post

def _match(text: str, pattern: str) -> bool:
    if not text:
        return False
    try:
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    except re.error:
        # fallback: substring match if regex invalid
        return pattern.lower() in text.lower()

class Command(BaseCommand):
    help = "Scan NEW posts using keywords (INCLUDE/EXCLUDE). Set flag_y and status."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Max posts per run")

    def handle(self, *args, **options):
        limit = max(1, min(options["limit"], 2000))

        includes = list(Keyword.objects.filter(enabled=True, type=Keyword.INCLUDE))
        excludes = list(Keyword.objects.filter(enabled=True, type=Keyword.EXCLUDE))

        qs = Post.objects.filter(status=Post.NEW).order_by("created_at")[:limit]
        count = 0

        for p in qs:
            hay_title = p.title or ""
            hay_desc = p.description or ""
            hay_both = f"{hay_title}\n{hay_desc}".strip()

            # EXCLUDE first: if any exclude matches -> drop
            excluded_by = None
            for k in excludes:
                target = hay_title if k.match_field == Keyword.TITLE else hay_desc if k.match_field == Keyword.DESCRIPTION else hay_both
                if _match(target, k.pattern):
                    excluded_by = k.pattern
                    break

            if excluded_by:
                p.flag_y = False
                p.flag_reason = f"EXCLUDE:{excluded_by}"[:200]
                p.status = Post.DROPPED
                p.save(update_fields=["flag_y", "flag_reason", "status"])
                count += 1
                continue

            included_by = None
            for k in includes:
                target = hay_title if k.match_field == Keyword.TITLE else hay_desc if k.match_field == Keyword.DESCRIPTION else hay_both
                if _match(target, k.pattern):
                    included_by = k.pattern
                    break

            if included_by:
                p.flag_y = True
                p.flag_reason = f"INCLUDE:{included_by}"[:200]
                p.status = Post.SCANNED
            else:
                p.flag_y = False
                p.flag_reason = "NO_KEYWORD"
                p.status = Post.DROPPED

            p.save(update_fields=["flag_y", "flag_reason", "status"])
            count += 1

        self.stdout.write(self.style.SUCCESS(f"scanned={count}"))
