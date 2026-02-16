# Moderation Service

## Setup

1. Создать БД: `sudo -u postgres psql -f scripts/create_db.sql`
2. Миграции: `pgmigrate -c "postgresql://moderation:moderation@localhost:5432/moderation" -d migrations -t latest migrate`
3. Запустить Kafka (Redpanda): `docker-compose up -d`
4. Запуск API: `uvicorn main:app --reload`
5. Запуск воркера: `python -m workers.moderation_worker`

## API

- `GET /` — проверка
- `POST /predict` — предсказание по полным данным
- `POST /simple_predict` — предсказание по item_id (данные из БД)
- `POST /async_predict` — асинхронная модерация (отправка в Kafka)
- `GET /moderation_result/{task_id}` — получение статуса модерации

## Kafka

- Брокер: `localhost:9092`
- Топики: `moderation`, `moderation_dlq`
- Консоль: http://localhost:8080

## Тесты

```bash
# Без БД (6 тестов)
pytest tests/ -v

# С PostgreSQL (все тесты)
pgmigrate -c "postgresql://moderation_test:moderation_test@localhost:5432/moderation_test" -d migrations -t latest migrate
pytest tests/ -v
```

## Makefile команды

- `make up` — запустить Kafka
- `make down` — остановить Kafka
- `make migrate` — применить миграции
- `make migrate-test` — применить миграции для тестовой БД
- `make worker` — запустить воркер
- `make test` — запустить тесты
