-- Migracion manual de la tabla antigua al perfil simplificado.
-- No es un script de inicializacion ni debe ejecutarse en cada arranque.
-- Pausa el servicio Clients antes de comenzar para evitar nuevas escrituras.
-- Ejecuta los bloques uno por uno en tu cliente MySQL.
-- Si un bloque falla, detente y no ejecutes los siguientes.

-- 1. Confirmar que estas en la base correcta y que existen las columnas antiguas.
USE clients;

SHOW COLUMNS FROM clients;

-- Si la tabla ya tiene solo user_id, full_name, email, phone, address,
-- email_verified y active, ya esta actualizada y no debes continuar.

-- 2. Copiar la estructura y TODOS los datos antes de quitar columnas.
-- No se usa IF NOT EXISTS: un respaldo anterior no debe sobrescribirse.
CREATE TABLE clients_backup_before_simplification LIKE clients;

INSERT INTO clients_backup_before_simplification
SELECT * FROM clients;

-- 3. Verificar el respaldo. Ambos conteos deben ser iguales.
-- Si no coinciden, detente. Manten Clients pausado hasta terminar.
SELECT
    (SELECT COUNT(*) FROM clients) AS original_rows,
    (SELECT COUNT(*) FROM clients_backup_before_simplification) AS backup_rows;

-- 4. Quitar unicamente los campos que el perfil actual ya no utiliza.
-- Los valores antiguos quedan guardados en la tabla de respaldo.
-- ALTER TABLE confirma cambios en MySQL: ROLLBACK no deshace este bloque.
ALTER TABLE clients
    DROP COLUMN run,
    DROP COLUMN commune,
    DROP COLUMN province,
    DROP COLUMN region,
    DROP COLUMN birth_date,
    DROP COLUMN sex,
    DROP COLUMN latitude,
    DROP COLUMN longitude,
    DROP COLUMN address_verified;

-- 5. Confirmar las siete columnas actuales y que se conservaron las filas.
SHOW COLUMNS FROM clients;

SELECT
    (SELECT COUNT(*) FROM clients) AS current_rows,
    (SELECT COUNT(*) FROM clients_backup_before_simplification) AS backup_rows;

-- Conserva el respaldo hasta verificar lectura y creacion de perfiles.
-- No se modifica user_id ni las relaciones con email_tokens.
-- No se cambian pedidos, pagos, usuarios ni productos.
-- No vuelvas a ejecutar esta migracion despues de aplicarla.
