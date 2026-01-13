import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

from core.models import Source, Post


def _get_text(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _parse_pubdate(pub_date_str: str):
    if not pub_date_str:
        return None
    try:
        dt = parsedate_to_datetime(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


class Command(BaseCommand):
    help = "Ingest latest posts from RSSHub /twitter/user/<username> into Post table (dedup by link)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run once and exit.")
        parser.add_argument("--sleep", type=int, default=30, help="Loop sleep seconds (default 30).")

    def handle(self, *args, **options):
        base_url = os.getenv("RSSHUB_BASE_URL", "http://host.docker.internal:1200").rstrip("/")
        run_once = options["once"]
        sleep_s = options["sleep"]

        self.stdout.write(self.style.SUCCESS(f"RSSHUB_BASE_URL={base_url}"))

        while True:
            now = dj_tz.now()
            sources = Source.objects.filter(enabled=True)
            for src in sources:
                if src.last_polled_at and (now - src.last_polled_at).total_seconds() < src.poll_interval_sec:
                    continue

                limit = max(1, min(int(src.limit_items), 50))
                url = f"{base_url}/twitter/user/{src.username}?limit={limit}"

                try:
                    r = requests.get(url, timeout=20)
                    r.raise_for_status()
                except Exception as e:
                    self.stderr.write(f"[{src.username}] fetch error: {e}")
                    src.last_polled_at = dj_tz.now()
                    src.save(update_fields=["last_polled_at"])
                    continue

                try:
                    root = ET.fromstring(r.text)
                except Exception as e:
                    self.stderr.write(f"[{src.username}] XML parse error: {e}")
                    src.last_polled_at = dj_tz.now()
                    src.save(update_fields=["last_polled_at"])
                    continue

                channel = root.find("channel")
                if channel is None:
                    self.stderr.write(f"[{src.username}] No <channel> in RSS")
                    src.last_polled_at = dj_tz.now()
                    src.save(update_fields=["last_polled_at"])
                    continue

                items = channel.findall("item")
                new_count = 0

                for item in items:
                    link = _get_text(item, "link")
                    title = _get_text(item, "title")
                    desc = _get_text(item, "description")
                    pub_date = _parse_pubdate(_get_text(item, "pubDate"))

                    if not link:
                        continue

                    # Dedup by unique link
                    obj, created = Post.objects.get_or_create(
                        link=link,
                        defaults={
                            "source": src,
                            "title": title,
                            "description": desc,
                            "pub_date": pub_date,
                            "status": Post.NEW,
                        },
                    )
                    if created:
                        new_count += 1
                    else:
                        # Non sovrascrivo contenuti già presenti (evita rimescolamenti)
                        pass

                src.last_polled_at = dj_tz.now()
                src.save(update_fields=["last_polled_at"])

                self.stdout.write(f"[{src.username}] items={len(items)} new={new_count}")

            if run_once:
                break
            time.sleep(max(5, sleep_s))
