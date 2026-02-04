import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://moderation_test:moderation_test@localhost:5432/moderation_test",
)
