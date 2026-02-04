#!/bin/bash
cd "$(dirname "$0")/.."
DB_URL="${DATABASE_URL:-postgresql://moderation:moderation@localhost:5432/moderation}"
pgmigrate -c "$DB_URL" -d migrations -t latest migrate
