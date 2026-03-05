# Moderation Service

## Setup

1. БД и миграции: `pgmigrate -c "postgresql://moderation:moderation@localhost:5433/moderation" -d migrations -t latest migrate`
2. Сервисы: `docker compose up -d`
3. API: `uvicorn main:app --host 0.0.0.0 --port 8000`
4. Воркер: `python -m workers.moderation_worker`

## API

- `GET /` — проверка
- `POST /predict` — предсказание по полным данным
- `POST /simple_predict` — предсказание по item_id
- `POST /async_predict` — асинхронная модерация
- `GET /moderation_result/{task_id}` — статус модерации
- `POST /close` — закрытие объявления
- `GET /metrics` — метрики Prometheus

## Мониторинг

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / admin)
- Дашборд: Import → `grafana/dashboard.json`

## Kafka

- Брокер: localhost:9092
- Консоль: http://localhost:8080

## Тесты

```bash
pytest tests/ -v -m "not integration"
pytest tests/ -v -m integration
```
