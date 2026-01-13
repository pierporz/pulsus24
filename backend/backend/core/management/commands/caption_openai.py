import os
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from openai import OpenAI

from core.models import Post


def _clip_200(s: str) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s[:200]


class Command(BaseCommand):
    help = "Generate caption (<=200 chars) + sentiment (up/down/neutral) for SCANNED posts with flag_y=True."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20, help="Max posts per run")

    def handle(self, *args, **options):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing in environment")

        client = OpenAI(api_key=api_key)

        limit = max(1, min(options["limit"], 100))

        qs = (
            Post.objects
            .filter(status=Post.SCANNED, flag_y=True, caption="")
            .order_by("created_at")[:limit]
        )

        done = 0
        for p in qs:
            text = (p.description or p.title or "").strip()
            if not text:
                text = p.link

            prompt = f"""
Testo post:
{text}

Produce exclusively a JSON object with those keys:
- caption: english string max 200 chars
- sentiment: decide if "up", "down", "neutral" 
Niente altro.
""".strip()

            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Answer JUST with a valid JSON object"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )

                out = (resp.choices[0].message.content or "").strip()
                if not out.startswith("{"):
                    raise ValueError(f"Non-JSON response: {out[:160]}")

                data = json.loads(out)

                caption = _clip_200(data.get("caption", ""))
                sentiment = (data.get("sentiment", "neutral") or "neutral").strip().lower()
                if sentiment not in ("up", "down", "neutral"):
                    sentiment = "neutral"

                p.caption = caption
                p.sentiment = sentiment
                p.ai_model = model
                p.captioned_at = timezone.now()
                p.ai_error = ""
                p.status = Post.CAPTIONED
                p.save(update_fields=[
                    "caption", "sentiment", "ai_model", "captioned_at", "ai_error", "status"
                ])

                done += 1
                self.stdout.write(f"[OK] {p.id} {sentiment} {caption}")

            except Exception as e:
                p.ai_error = str(e)[:2000]
                p.save(update_fields=["ai_error"])
                self.stderr.write(f"[ERR] {p.id} {e}")

        self.stdout.write(self.style.SUCCESS(f"captioned={done}"))
