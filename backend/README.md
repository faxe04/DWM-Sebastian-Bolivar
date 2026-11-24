# Café & Aroma — Backend

Proyecto del caso 4, Café & Aroma, para Desarrollo Web y Móvil, Evaluación 2.

**Autor:** Sebastián Bolívar
**NRC:** 8480

El sistema permite consultar el catálogo de la cafetería, gestionar clientes,
crear pedidos, reservar stock y registrar pagos de demostración. Incluye
administración de usuarios, productos, ventas, boletas y despacho.

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python, FastAPI y Uvicorn | API Gateway, Auth y servicios de negocio. |
| Pydantic | Validación de entradas y modelos de datos. |
| HTTPX | Comunicación HTTP entre servicios. |
| MySQL 8.4 y MySQL Connector/Python | Persistencia y consultas SQL parametrizadas. |
| HashiCorp Vault | Almacenamiento de secretos de integración utilizados por el Gateway. |
| Node.js, Apollo Server, Express y GraphQL | Agregación de información de varios servicios. |
| Docker y Docker Compose | Contenedores, red privada y despliegue local. |
| React, Vite y React Router | Interfaz web y navegación del frontend. |
| unittest y FastAPI TestClient | Pruebas automatizadas de las APIs y reglas de negocio. |

Las dependencias Python están fijadas en `requirements.txt`. Las dependencias
JavaScript se definen en los respectivos `package.json` y `package-lock.json`.

## Estructura

```text
backend/
├── auth/                    Cuentas, sesiones y permisos de administración
├── gateway/                 Entrada pública, autenticación y enrutamiento
├── graphql/                 Schema, resolvers y límites de consultas
├── services/
│   ├── inventory/           Catálogo, stock y reservas
│   ├── clients/             Perfiles y verificación de correo
│   ├── orders/              Pedidos, ventas, boletas y despacho
│   └── payments/            Intentos de pago, eventos y reembolsos dummy
├── infrastructure/
│   ├── mysql/               Creación de tablas y catálogo inicial de 10 productos
│   │   └── migrations/      Cambios manuales para bases existentes
│   └── PlataformaCafeteria.dsl  Modelo de componentes y despliegue
├── scripts/                 Preparación e inicialización del entorno
├── tests/                   Pruebas aisladas y pruebas de integración
├── request_logging.py       Logs HTTP con identificador de solicitud
├── requirements.txt         Dependencias Python
├── Dockerfile               Imagen de los servicios Python
├── compose.yaml             Despliegue del backend en Docker
├── compose.local.yaml       Acceso local opcional a MySQL y Vault
├── compose.tls.yaml         HTTPS local opcional para Gateway
└── .env.example             Ejemplo de configuración
```

Los servicios Python separan sus responsabilidades en `main.py` (endpoints),
`schemas.py` (modelos), `db.py` (SQL), `security.py` (permisos y secretos) y
`config.py` (configuración). El frontend está en `frontend/`, junto a `backend/`.

Un contenedor MySQL aloja cinco bases, cada una con su usuario
propio y permisos limitados:

| Base | Tablas principales |
|---|---|
| `auth` | `users`, `sessions` |
| `inventory` | `products`, `reservations` |
| `clients` | `clients`, `email_tokens`, `mail_outbox`, `receipt_deliveries` |
| `orders` | `orders`, `cash_registers`, `sales` |
| `payments` | `payments`, `payment_orders`, `payment_events` |

Cada servicio modifica su propia base. Las relaciones entre servicios utilizan
IDs y llamadas HTTP. Los pedidos conservan los productos y precios históricos
en JSON. El volumen `mysql_data` conserva los datos al detener los contenedores.

**Función de los scripts:**

| Script | Responsabilidad |
|---|---|
| `prepare.py` | Genera archivos de secretos, ejemplos `.env` y certificado local si faltan. Conserva los archivos existentes. |
| `init_auth.py` | Crea la base y el usuario MySQL de Auth, sus tablas y las cuentas de demostración ausentes. |
| `init_services.py` | Crea las bases de Clients, Orders y Payments, sus usuarios y las tablas adicionales de reservas, ventas y correo. |
| `init_vault.py` | Carga los secretos del Gateway en Vault y configura su token con una política de lectura limitada. |
| `load_test.py` | Ejecuta consultas concurrentes al catálogo y registra latencia, rendimiento y errores. Puede tomar muestras de recursos de Docker. |

Compose ejecuta los procesos `init_*` al desplegar. Su finalización con código 0
es normal: son tareas de preparación, no servidores permanentes.

## Flujo, operaciones y permisos

El navegador llama al Gateway bajo `/api/v1`. En las rutas protegidas, el Gateway
consulta a Auth para validar la sesión, obtiene de Vault el secreto del destino
y transmite la identidad verificada. El servicio receptor comprueba la clave
interna y aplica los permisos y reglas correspondientes.

1. El visitante consulta el catálogo y puede registrar una cuenta de tipo `client`.
2. El usuario inicia sesión con `username` y `password`; Auth devuelve un token.
3. El cliente crea su perfil con `full_name`, `email`, `phone` y `address`, y verifica
   su correo mediante el token disponible en la bandeja de demostración del admin.
4. Al crear un pedido, Orders exige el perfil y correo verificado, solicita la
   reserva a Inventory y calcula el total con los precios oficiales. Para delivery
   se exige una dirección; no se comprueba un radio geográfico.
5. Payments consulta el pedido y crea un intento con su importe oficial. La prueba
   de pago genera un evento firmado, valida importe y moneda y, si es aprobado,
   notifica a Orders para dejar el pedido en `PAID`.
6. El administrador puede registrar la venta, emitir una boleta demo y avanzar
   la preparación y entrega.

Las solicitudes de creación de pedidos y pagos requieren `Idempotency-Key`.
Reintentar la misma operación con su clave evita duplicados. Después de un pago
`REJECTED`, el backend permite crear otro intento para el mismo pedido con una
clave nueva. Una aprobación puede reintentarse por la simulación administrativa
para completar la notificación a Orders si hubo un fallo de comunicación.

Estados del pedido: `CREATING → PENDING_PAYMENT → PAID → PREPARING → READY →
OUT_FOR_DELIVERY → DELIVERED`. Para retiro, `READY` pasa directamente a
`DELIVERED`. Una cancelación impaga bloquea nuevos pagos y libera stock. Después
del pago, el cliente solicita la cancelación y el admin puede autorizar el
reembolso dummy antes de comenzar la preparación.

Todas las rutas de la tabla llevan el prefijo `/api/v1`:

| Operación y ruta | Método | Acceso |
|---|---|---|
| Catálogo: `/products`, `/products/{id}` | GET | Anónimo. |
| Productos: `/admin/products` y `/admin/products/{id}` | GET/POST en colección; PUT/DELETE por ID | Admin. |
| Cuenta: `/auth/register`, `/auth/login` | POST | Anónimo; el registro crea un cliente. |
| Sesión: `/auth/me`, `/auth/logout` | GET, POST | Usuario autenticado; logout revoca el token. |
| Usuarios: `/admin/users`, `/admin/users/{id}` | GET/POST en colección; GET/PUT/DELETE por ID | Admin; se protege al último administrador activo. |
| Perfil: `/clients/me` | GET/POST/PUT | Perfil del usuario autenticado. |
| Correo: `/clients/me/verification`, `/clients/verify-email` | POST | Sesión para solicitar; token de verificación para confirmar. |
| Clientes: `/admin/clients`, `/admin/clients/{id}` | GET en colección; GET/POST/PUT/DELETE por ID | Admin. |
| Verificación asistida: `/admin/clients/{id}/verification`; bandeja: `/admin/mailbox` | POST; GET | Admin, modo demostración. |
| Pedidos: `/orders`, `/orders/{id}` | GET/POST en colección; GET por ID | Recursos propios; admin puede consultar por ID. |
| Cancelación: `/orders/{id}/cancel` | POST | Propietario o admin, según estado. |
| Gestión: `/admin/orders`, `/admin/orders/{id}/status` | GET; PUT | Admin, respetando transiciones. |
| Pagos: `/payments`, `/payments/{id}` | GET/POST en colección; GET por ID | Recursos propios; admin puede consultar por ID. |
| Pago de prueba: `/payments/{id}/test` | POST | Propietario o admin; solo `DEMO_MODE=true`. |
| Gestión de pagos: `/admin/payments`, `/admin/payments/{id}/simulate` | GET; POST | Admin; simulación solo en modo demo. |
| Aviso de pago: `/payments/webhook` | POST | Firma HMAC; no utiliza la sesión del navegador. |
| Venta: `/admin/sales`; cajas: `/admin/cash-registers` | POST; GET | Admin; la venta requiere un pedido pagado. |
| Boleta: `/orders/{id}/receipt`, `/orders/{id}/receipt/print` | GET | Propietario o admin. |
| Reporte: `/admin/sales/report`; despacho: `/admin/dispatch`, `/admin/orders/{id}/dispatch` | GET | Admin. |
| Agregación: `/graphql` | POST | Sesión y permisos por recurso y campo. |

GraphQL permite consultar `orderSummary`, combinando Orders, Clients y Payments,
sin consultar directamente sus bases. El campo `requestKey` es exclusivo de admin.

Los pagos, reembolsos, correos y boletas son de demostración: no se mueve dinero ni
se envían correos reales. En `/payments/{id}/test`, `0000000000000001` aprueba y
`0000000000000002` rechaza. Solo se deben usar esos números ficticios. El endpoint
administrativo `/simulate` admite `APPROVED` o `REJECTED`.

Las contraseñas se guardan con hash y sal; la base conserva la huella del token de
sesión. Las rutas internas requieren secretos de servicio y no se publican como
APIs del navegador. Los logs HTTP incluyen ruta, resultado, duración e identificador
de solicitud, sin registrar contraseñas ni cuerpos de las solicitudes.

## Instalación y setup

**Requisitos:** Docker Desktop iniciado, Docker Compose, Python 3.11 o superior y
PowerShell. Para ejecutar el frontend o las pruebas de GraphQL fuera de Docker,
se necesita Node.js 24 y npm. No es necesario instalar MySQL en Windows: Compose
inicia una instancia propia.

Los comandos siguientes se ejecutan desde la raíz del repositorio, que contiene
`backend/` y `frontend/`.

**Preparación:**

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m backend.scripts.prepare
```

**Configuración:**

- `.env.example` documenta las variables; `prepare.py` crea los `.env` ausentes.
- En Docker, Compose entrega las variables de cada contenedor y monta los secretos
  de `.runtime` bajo `/run/secrets`. Las variables `_FILE` señalan esos archivos.
- Los servicios Python admiten el valor directo o su archivo mediante `config.py`.
  Si existe una variable `_FILE`, se utiliza el archivo indicado.
- Para ejecución individual, cada servicio necesita `DB_HOST`, `DB_PORT`, `DB_USER`,
  `DB_PASS`, `DB_NAME`, las URLs de sus dependencias y las claves de sus integraciones.
- Gateway utiliza `VAULT_ADDR` y `VAULT_TOKEN` o `VAULT_TOKEN_FILE`. Las claves que
  obtiene de Vault deben coincidir con las configuradas en los servicios receptores.
- `DEMO_MODE=true` habilita las funciones de pago y correo ficticios.
- Los `.env` y `.runtime` son locales y no deben subirse al repositorio. No regenerar
  las claves de una instalación conservando su base sin coordinar su actualización.

**Despliegue local HTTP:**

```powershell
docker compose --env-file backend/.env -f backend/compose.yaml up -d --build
docker compose --env-file backend/.env -f backend/compose.yaml ps
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/api/v1/products
```

Gateway publica `http://127.0.0.1:8000`. Los demás servicios permanecen en la red
privada. El archivo `compose.local.yaml` es una alternativa para desarrollo que
publica MySQL en `127.0.0.1:3307` y Vault en `127.0.0.1:8200`; no se necesita para
el despliegue completo anterior.

MySQL conserva los datos existentes. Los scripts de creación no modifican tablas
ya creadas: los cambios de una base anterior se aplican revisando los archivos de
`infrastructure/mysql/migrations/`. La migración de Clients incluye respaldo y
pasos manuales; no debe repetirse si la tabla ya tiene el esquema actual. El script
de catálogo agrega los productos ausentes sin reemplazar los existentes.

**Cuentas de demostración:**

| Usuario | Rol | Archivo local de contraseña |
|---|---|---|
| `admin-demo` | `admin` | `backend/.runtime/demo_admin_password` |
| `cliente-demo` | `client` | `backend/.runtime/demo_client_password` |

Las contraseñas se generan por instalación. Una cuenta recién creada no tiene
perfil comercial: antes de comprar hay que crearlo y verificar su correo usando
las operaciones descritas en el flujo.

**Logs y detención:**

```powershell
docker compose --env-file backend/.env -f backend/compose.yaml logs -f gateway
```

Abrir otras terminales y reemplazar `gateway` por `auth`, `inventory`, `clients`,
`orders` o `payments` para seguir cada componente. `Ctrl+C` cierra el seguimiento,
no el contenedor. Para detener el backend conservando los datos:

```powershell
docker compose --env-file backend/.env -f backend/compose.yaml stop
```

Vault funciona en modo dev y su token de Gateway dura 24 horas. Si expira, volver
a ejecutar la inicialización con Vault activo:

```powershell
docker compose --env-file backend/.env -f backend/compose.yaml run --rm vault-init
```

**HTTPS local:** el archivo adicional cambia el Gateway a HTTPS en el mismo puerto:

```powershell
docker compose --env-file backend/.env -f backend/compose.yaml -f backend/compose.tls.yaml up -d --build
curl.exe --cacert backend/.runtime/localhost.crt https://localhost:8000/health
```

El certificado generado es local y dura 30 días. Para usar HTTPS desde el navegador
hay que confiar en ese certificado y ajustar las URLs del frontend. El despliegue
es académico y local; las comunicaciones internas utilizan HTTP en la red privada.

**Comprobaciones del setup:**

```powershell
backend/.venv/Scripts/python.exe -B -m unittest discover -s backend/tests -p "test_*.py" -v
npm --prefix backend/graphql ci
npm --prefix backend/graphql test
```

Estas pruebas utilizan dependencias simuladas o una base temporal. Para comprobar
el recorrido con servicios y MySQL reales, configurar `DEMO_ADMIN_PASSWORD` en la
terminal con la contraseña local del administrador y ejecutar:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
backend/.venv/Scripts/python.exe -B -m unittest backend.tests.integration_commerce -v
```

La integración crea datos ficticios y comprueba permisos, pedidos, pagos, stock y
cancelaciones. 
El uso de HTTPS es opcional, pero en caso de utilizarse, configurar además `API_CA_FILE` con la ruta al
certificado y cambiar `API_BASE_URL` al origen HTTPS.

## Uso de LLM

Se utilizaron modelos de lenguaje (LLM) como apoyo para formular el esquema de
base de datos, generar pruebas y completar endpoints siguiendo la estructura establecida. 
Los resultados se revisaron y modificaron manualmente para ajustarlos al caso de la cafetería, 
simplificar la lógica y corregir errores.

También se utilizó IA para redactar este README y obtener orientación sobre la
configuración de Docker. Las solicitudes se realizaron con instrucciones
específicas sobre los objetivos, el alcance y la estructura esperada, con el
propósito de optimizar el trabajo manteniendo la revisión y validación manual
de los resultados.
