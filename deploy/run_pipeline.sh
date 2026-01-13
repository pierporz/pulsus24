#!/bin/sh
set -eu

DIR=$(cd "$(dirname "$0")" && pwd)

docker compose -f "$DIR/docker-compose.yml" exec -T django sh -c "python manage.py ingest_rsshub --once && python manage.py scan_keywords --limit 200 && python manage.py caption_openai --limit 20 && python manage.py publish_wordpress --limit 10"
