import httpx
from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from . import config
from .schemas import LoginRequest, RegistrationRequest
from .security import authenticate_client, require_admin, security, get_gateway_secrets
from fastapi.middleware.cors import CORSMiddleware

from backend.request_logging import install


app = FastAPI(title="Aroma & Café - API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key",],
)


# ===== Reenvio HTTP =====
def forward(response):
    # Conserva respuestas útiles (200, 201, 404, 422...), sin publicar fallos internos.
    if response.status_code >= 500 or 300 <= response.status_code < 400:
        raise HTTPException(502, "El servicio no pudo completar la solicitud")
    
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={"Content-Type": response.headers.get("content-type", "application/json")},
    )


async def proxy(path: str, request: Request, identity=None, service="inventory"):
    target = config.ROUTES.get(service)

    if not target:
        raise HTTPException(503, "Servicio no configurado")

    values = await get_gateway_secrets()
    secret = values.get(f"{service}_gateway_secret")

    if not isinstance(secret, str) or not secret:
        raise HTTPException(503, "Falta secreto del servicio")

    if not target:
        raise HTTPException(503, "Servicio no configurado")
    
    if not isinstance(secret, str) or not secret:
        raise HTTPException(503, "Falta secreto del servicio")

    headers = {
        "X-Gateway-Secret": secret,
        "X-Request-ID": request.state.request_id,
    }

    if identity is not None:
        headers["X-Authenticated-User"] = identity["user_id"]
        headers["X-Authenticated-Roles"] = ",".join(identity["roles"])

    if request.method == "POST" and path in ("orders", "payments"):
        if "Idempotency-Key" in request.headers:
            headers["Idempotency-Key"] = request.headers["Idempotency-Key"]

    if request.method == "POST" and path == "payments/webhook":
        if "X-Payment-Signature" in request.headers:
            headers["X-Payment-Signature"] = request.headers["X-Payment-Signature"]

    if request.method in {"POST", "PUT"}:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise HTTPException(415, "Se requiere application/json")
        
        headers["Content-Type"] = "application/json"

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, "Solicitud demasiado grande")
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method=request.method,
                url=f"{target.rstrip('/')}/{path.lstrip('/')}",
                params=request.query_params,
                content=bytes(body),
                headers=headers,
            )

    except httpx.RequestError:
        raise HTTPException(503, "Backend no disponible")
    
    return forward(response)


async def auth_proxy(path, request, identity):
    values = await get_gateway_secrets()
    auth_secret = values.get("auth_introspection_secret")

    if not isinstance(auth_secret, str) or not auth_secret:
        raise HTTPException(
            status_code=503, 
            detail="Falta secreto de Auth"
        )
    
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 16384:
            raise HTTPException(413, "Solicitud demasiado grande")
        
    headers = {
        "X-Gateway-Auth-Secret": auth_secret,
        "X-Authenticated-User": identity["user_id"], 
        "X-Authenticated-Roles": ",".join(identity["roles"]),
        "X-Request-ID": request.state.request_id
    }
    if request.method in ("POST", "PUT"):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise HTTPException(415, "Se requiere application/json")
        
        headers["Content-Type"] = "application/json"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.request(request.method, config.AUTH_SERVICE_URL.rstrip("/") + path, params=request.query_params, content=bytes(body), headers=headers)

    except httpx.RequestError:
        raise HTTPException(503, "Auth no disponible")
    
    return forward(response)


# ===== System =====
@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


# ===== Auth =====
@app.post("/api/v1/auth/login")
async def login(body: LoginRequest, request: Request):
    values = await get_gateway_secrets()
    auth_secret = values.get("auth_introspection_secret")

    if not isinstance(auth_secret, str) or not auth_secret:
        raise HTTPException(
            status_code=503, 
            detail="Falta secreto de Auth"
        )
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{config.AUTH_SERVICE_URL.rstrip('/')}/login",
                headers={"X-Gateway-Auth-Secret": auth_secret,
                         "X-Request-ID": request.state.request_id},
                json=body.model_dump(),
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503, 
            detail="Authentication Service no disponible"
        )
    
    result = forward(response)
    result.headers["Cache-Control"] = "no-store"
    return result


@app.get("/api/v1/auth/me")
async def me(identity=Depends(authenticate_client)):
    return {"user_id": identity["user_id"], "roles": identity["roles"]}


@app.post("/api/v1/auth/logout")
async def logout(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if credentials is None or len(credentials.credentials) > 512:
        raise HTTPException(
            status_code=401, 
            detail="Bearer token requerido"
        )
    
    values = await get_gateway_secrets()
    auth_secret = values.get("auth_introspection_secret")

    if not isinstance(auth_secret, str) or not auth_secret:
        raise HTTPException(
            status_code=503, 
            detail="Falta secreto de Auth"
        )
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{config.AUTH_SERVICE_URL.rstrip('/')}/logout",
                headers={
                    "X-Gateway-Auth-Secret": auth_secret, 
                    "X-Request-ID": request.state.request_id
                },
                json={"token": credentials.credentials},
            )
    except httpx.RequestError:
        raise HTTPException(503, "Authentication Service no disponible") from None
    return forward(response)


@app.post("/api/v1/auth/register")
async def register(body: RegistrationRequest, request: Request):
    values = await get_gateway_secrets()
    auth_secret = values.get("auth_introspection_secret")
    
    if not isinstance(auth_secret, str) or not auth_secret:
        raise HTTPException(
            status_code=503, 
            detail="Falta secreto de Auth"
        )
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(auth_secret.rstrip("/") + "/register", json=body.model_dump(),
                headers={
                    "X-Gateway-Auth-Secret": auth_secret,
                    "X-Request-ID": request.state.request_id})
    except httpx.RequestError:
        raise HTTPException(503, "Auth no disponible") from None
    return forward(response)


@app.api_route("/api/v1/admin/users", methods=["GET","POST"])
async def users(request: Request, identity=Depends(require_admin)):
    return await auth_proxy("/admin/users", request, identity)


@app.api_route("/api/v1/admin/users/{user_id}", methods=["GET","PUT","DELETE"])
async def user(request: Request, user_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await auth_proxy(f"/admin/users/{user_id}", request, identity)


# ===== Inventory =====
@app.get("/api/v1/products")
async def list_products(request: Request):
    return await proxy("products", request)


@app.get("/api/v1/products/{product_id}")
async def get_product(request: Request, product_id: int = Path(gt=0)):
    return await proxy(f"products/{product_id}", request)


@app.api_route("/api/v1/admin/products", methods=["GET", "POST"])
async def admin_products(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/products", request, identity)


@app.api_route("/api/v1/admin/products/{product_id}", methods=["PUT", "DELETE"])
async def admin_product(request: Request, product_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/products/{product_id}", request, identity)


# ===== Clients =====
@app.api_route("/api/v1/clients/me", methods=["GET", "POST", "PUT"])
async def client_profile(request: Request, identity=Depends(authenticate_client)):
    return await proxy("clients/me", request, identity, "clients")


@app.post("/api/v1/clients/me/verification")
async def send_verification(request: Request, identity=Depends(authenticate_client)):
    return await proxy("clients/me/verification", request, identity, "clients")


@app.post("/api/v1/clients/verify-email")
async def verify_email(request: Request):
    return await proxy("clients/verify-email", request, service="clients")


@app.get("/api/v1/admin/clients")
async def admin_clients(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/clients", request, identity, "clients")


@app.post("/api/v1/admin/clients/{user_id}")
async def create_client(request: Request, user_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/clients/{user_id}", request, identity, "clients")


@app.api_route("/api/v1/admin/clients/{user_id}", methods=["GET", "PUT", "DELETE"])
async def admin_client(request: Request, user_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/clients/{user_id}", request, identity, "clients")


@app.post("/api/v1/admin/clients/{user_id}/verification")
async def client_verification(request: Request, user_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/clients/{user_id}/verification", request, identity, "clients")


@app.post("/api/v1/admin/clients/{user_id}/address-approval")
async def approve_address(request: Request, user_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/clients/{user_id}/address-approval", request, identity, "clients")


@app.get("/api/v1/admin/mailbox")
async def mailbox(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/mailbox", request, identity, "clients")


# ===== Orders =====
@app.api_route("/api/v1/orders", methods=["GET", "POST"])
async def orders(request: Request, identity=Depends(authenticate_client)):
    return await proxy("orders", request, identity, "orders")


@app.get("/api/v1/orders/{order_id}")
async def order(request: Request, order_id: int = Path(gt=0), identity=Depends(authenticate_client)):
    return await proxy(f"orders/{order_id}", request, identity, "orders")


@app.post("/api/v1/orders/{order_id}/cancel")
async def cancel_order(request: Request, order_id: int = Path(gt=0), identity=Depends(authenticate_client)):
    return await proxy(f"orders/{order_id}/cancel", request, identity, "orders")


@app.get("/api/v1/admin/orders")
async def admin_orders(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/orders", request, identity, "orders")


@app.put("/api/v1/admin/orders/{order_id}/status")
async def order_status(request: Request, order_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/orders/{order_id}/status", request, identity, "orders")


# ===== Payments =====
@app.api_route("/api/v1/payments", methods=["GET", "POST"])
async def payments(request: Request, identity=Depends(authenticate_client)):
    return await proxy("payments", request, identity, "payments")


@app.post("/api/v1/payments/webhook")
async def payment_webhook(request: Request):
    return await proxy("payments/webhook", request, service="payments")


@app.get("/api/v1/payments/{payment_id:int}")
async def payment(request: Request, payment_id: int = Path(gt=0), identity=Depends(authenticate_client)):
    return await proxy(f"payments/{payment_id}", request, identity, "payments")


@app.get("/api/v1/admin/payments")
async def admin_payments(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/payments", request, identity, "payments")


@app.post("/api/v1/admin/payments/{payment_id}/simulate")
async def simulate_payment(request: Request, payment_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/payments/{payment_id}/simulate", request, identity, "payments")


@app.post("/api/v1/payments/{payment_id}/test")
async def test_payment(request: Request, payment_id: int = Path(gt=0), identity=Depends(authenticate_client)):
    return await proxy(f"payments/{payment_id}/test", request, identity, "payments")


# ===== GraphQL =====
@app.post("/api/v1/graphql")
async def graphql(request: Request, identity=Depends(authenticate_client)):
    return await proxy("graphql", request, identity, "graphql")


# ===== Ventas, boletas y despacho =====
@app.post("/api/v1/admin/sales")
async def sale(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/sales", request, identity, "orders")


@app.get("/api/v1/admin/cash-registers")
async def registers(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/cash-registers", request, identity, "orders")


@app.get("/api/v1/admin/sales/report")
async def report(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/sales/report", request, identity, "orders")


@app.get("/api/v1/admin/dispatch")
async def dispatch(request: Request, identity=Depends(require_admin)):
    return await proxy("admin/dispatch", request, identity, "orders")


@app.get("/api/v1/admin/orders/{order_id}/dispatch")
async def dispatch_document(request: Request, order_id: int = Path(gt=0), identity=Depends(require_admin)):
    return await proxy(f"admin/orders/{order_id}/dispatch", request, identity, "orders")


@app.get("/api/v1/orders/{order_id}/receipt")
async def receipt(request: Request, order_id: int = Path(gt=0), identity=Depends(authenticate_client)):
    return await proxy(f"orders/{order_id}/receipt", request, identity, "orders")


@app.get("/api/v1/orders/{order_id}/receipt/print")
async def receipt_document(request: Request, order_id: int = Path(gt=0), identity=Depends(authenticate_client)):
    return await proxy(f"orders/{order_id}/receipt/print", request, identity, "orders")


# Middleware
install(app)
