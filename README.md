## Setup

1. Создать БД: `sudo -u postgres psql -f scripts/create_db.sql`
2. Миграции: `pgmigrate -c "postgresql://moderation:moderation@localhost:5432/moderation" -d migrations -t latest migrate`
3. Запуск: `uvicorn main:app --reload`

## API

- `GET /` — проверка
- `POST /predict` — предсказание по полным данным
- `POST /simple_predict` — предсказание по item_id (данные из БД)

## Тесты

```bash
# Без БД
pytest tests/ -v

# С PostgreSQL 
pgmigrate -c "postgresql://moderation_test:moderation_test@localhost:5432/moderation_test" -d migrations -t latest migrate
pytest tests/ -v
```
