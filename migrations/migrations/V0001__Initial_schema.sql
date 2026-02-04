CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    is_verified_seller BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE ads (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER NOT NULL DEFAULT 0
);
