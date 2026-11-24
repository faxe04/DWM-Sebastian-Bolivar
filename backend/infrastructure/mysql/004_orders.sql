CREATE TABLE IF NOT EXISTS orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    request_key VARCHAR(100) NOT NULL,
    request_hash CHAR(64) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'CREATING',
    total BIGINT NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'CLP',
    delivery_method VARCHAR(20) NOT NULL,
    address_snapshot JSON NULL,
    items JSON NOT NULL,
    payment_id BIGINT UNSIGNED NULL,
    cancellation_reason VARCHAR(500) NULL,
    cancellation_requested BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY order_retry (user_id, request_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
