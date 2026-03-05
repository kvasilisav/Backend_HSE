#!/bin/bash
set -e
cd "$(dirname "$0")/.."
DB_URL="${DATABASE_URL:-postgresql://moderation:moderation@localhost:5432/moderation}"

# parse URL: postgresql://user:pass@host:port/dbname
if [[ "$DB_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
  export PGPASSWORD="${BASH_REMATCH[2]}"
  HOST="${BASH_REMATCH[3]}"
  PORT="${BASH_REMATCH[4]}"
  DB="${BASH_REMATCH[5]}"
  USER="${BASH_REMATCH[1]}"
else
  echo "Не удалось разобрать DATABASE_URL"
  exit 1
fi

echo "Миграции для $USER@$HOST:$PORT/$DB"
for f in migrations/migrations/V0001__Initial_schema.sql migrations/migrations/V0002__Create_moderation_results.sql migrations/migrations/V0003__Add_is_closed_to_ads.sql; do
  echo "  $f"
  psql -v ON_ERROR_STOP=1 -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -f "$f"
done
echo "Готово."
