CREATE TABLE IF NOT EXISTS cash_registers (
    id BIGINT UNSIGNED PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO cash_registers (id, name) VALUES
    (1, 'Caja virtual cafetería');

CREATE TABLE IF NOT EXISTS sales (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL UNIQUE,
    cashier_user_id BIGINT UNSIGNED NOT NULL,
    register_id BIGINT UNSIGNED NOT NULL,
    total BIGINT NOT NULL,
    receipt JSON NOT NULL,
    receipt_sent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (register_id) REFERENCES cash_registers (id),
    INDEX sales_period (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
