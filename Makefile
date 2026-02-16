.PHONY: up down migrate test worker

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	pgmigrate -c "postgresql://moderation:moderation@localhost:5432/moderation" -d migrations -t latest migrate

migrate-test:
	pgmigrate -c "postgresql://moderation_test:moderation_test@localhost:5432/moderation_test" -d migrations -t latest migrate

worker:
	python -m workers.moderation_worker

test:
	pytest tests/ -v
