import os
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Post


def _arrow_html(sentiment: str) -> str:
    s = (sentiment or "").strip().lower()
    if s == "up":
        return '<div style="color:#16a34a;font-weight:700;font-size:24px;line-height:1;margin-bottom:12px">▲</div>'
    if s == "down":
        return '<div style="color:#dc2626;font-weight:700;font-size:24px;line-height:1;margin-bottom:12px">▼</div>'
    return ""


def _normalize_twitter_url(url: str) -> str:
    u = (url or "").strip()
    # WordPress spesso embeda twitter.com ma NON x.com
    if u.startswith("https://x.com/"):
        u = "https://twitter.com/" + u[len("https://x.com/"):]
    elif u.startswith("http://x.com/"):
        u = "https://twitter.com/" + u[len("http://x.com/"):]
    return u


class Command(BaseCommand):
    help = "Publish posts to WP (content=arrow + tweet url on its own line for oEmbed)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        base = os.getenv("WP_BASE_URL", "").rstrip("/")
        user = os.getenv("WP_USERNAME", "")
        pwd = os.getenv("WP_APP_PASSWORD", "")
        if not base or not user or not pwd:
            raise RuntimeError("Missing WP_* env vars")

        limit = max(1, min(int(options["limit"]), 50))
        qs = (
            Post.objects
            .filter(status=Post.CAPTIONED, wp_post_id__isnull=True)
            .order_by("created_at")[:limit]
        )

        for p in qs:
            try:
                caption = (p.caption or "").strip() or "Market update"
                arrow = _arrow_html(p.sentiment)
                link_clean = _normalize_twitter_url(p.link)

                # IMPORTANTISSIMO: URL DA SOLO su una riga (niente <a>, niente [embed])
                content = f"{arrow}\n\n{link_clean}\n"

                payload = {
                    "title": caption[:120],
                    "content": content,
                    "status": "publish",
                }

                r = requests.post(
                    f"{base}/wp-json/wp/v2/posts",
                    auth=(user, pwd),
                    json=payload,
                    timeout=25,
                )
                r.raise_for_status()
                data = r.json()

                p.wp_post_id = data.get("id")
                p.published_at = timezone.now()
                p.wp_status = "OK"
                p.wp_error = ""
                p.status = Post.PUBLISHED
                p.save(update_fields=["wp_post_id", "published_at", "wp_status", "wp_error", "status"])

                self.stdout.write(f"[OK] wp_id={p.wp_post_id} local_id={p.id}")

            except Exception as e:
                p.wp_status = "ERROR"
                p.wp_error = str(e)[:2000]
                p.save(update_fields=["wp_status", "wp_error"])
                self.stderr.write(f"[ERR] publish {p.id}: {e}")
