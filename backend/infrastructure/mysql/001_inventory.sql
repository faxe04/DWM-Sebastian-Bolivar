USE inventory;


CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(1000) NOT NULL DEFAULT '',
    category VARCHAR(60) NOT NULL,
    price INT NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT positive_price CHECK (price > 0 AND price <= 100000000),
    CONSTRAINT valid_stock CHECK (stock >= 0 AND stock <= 1000000),
    INDEX catalog_filter (is_active, category, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Catalogo de demostracion. No reemplaza productos existentes.
INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Café Colombia', 'Café de origen, taza individual', 'cafe', 3500, 20, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Café Colombia' AND category = 'cafe'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Croissant clásico', 'Croissant de mantequilla', 'reposteria', 2800, 12, FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Croissant clásico' AND category = 'reposteria'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Café Espresso', 'Café intenso preparado al momento', 'cafe', 2490, 30, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Café Espresso' AND category = 'cafe'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Café Americano', 'Espresso con agua caliente', 'cafe', 2690, 25, FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Café Americano' AND category = 'cafe'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Café Latte', 'Espresso con leche y una capa suave de espuma', 'cafe', 2990, 25, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Café Latte' AND category = 'cafe'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Cappuccino', 'Espresso con leche y abundante espuma', 'cafe', 3290, 20, FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Cappuccino' AND category = 'cafe'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Café Mocha', 'Espresso con chocolate y leche', 'cafe', 3590, 20, FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Café Mocha' AND category = 'cafe'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Cheesecake Frutos Rojos', 'Porción de cheesecake con salsa de frutos rojos', 'reposteria', 3990, 15, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Cheesecake Frutos Rojos' AND category = 'reposteria'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Brownie de Chocolate', 'Brownie de chocolate, porción individual', 'reposteria', 2890, 18, FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Brownie de Chocolate' AND category = 'reposteria'
);

INSERT INTO products (name, description, category, price, stock, featured)
SELECT 'Muffin de Arándanos', 'Muffin esponjoso con arándanos', 'reposteria', 2490, 16, FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Muffin de Arándanos' AND category = 'reposteria'
);
