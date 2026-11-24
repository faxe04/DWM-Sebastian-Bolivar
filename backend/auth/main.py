from datetime import datetime, timedelta, timezone
import secrets
from fastapi import Depends, FastAPI, HTTPException, Request, Response, Path, Query
from fastapi.responses import JSONResponse
from mysql.connector import IntegrityError, Error as DatabaseError
from .schemas import RegistrationRequest
from . import config
from . import db
from .schemas import LoginRequest, IntrospectionRequest, UserCreate, UserUpdate
from .security import hash_password, verify_password, token_hash, verify_gateway, verify_clients, require_admin
from backend.request_logging import install # Middleware


app = FastAPI(
    title="Aroma & Café - Authentication Service",
    docs_url=None, 
    redoc_url=None, 
    openapi_url=None
)


@app.exception_handler(DatabaseError)
async def database_error(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=503, content={"detail": "Persistencia de Auth no disponible"})


# ===== System =====
@app.get("/health", dependencies=[Depends(verify_gateway)])
def health():
    return {"status": "ok", "service": "auth"}


@app.post("/login", dependencies=[Depends(verify_gateway)])
def login(request: LoginRequest, response: Response):
    user = db.get_user(request.username)

    if not user or not user["enabled"]:
        raise HTTPException(
            status_code=401, detail="Credenciales incorrectas"
        )

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=401, 
            detail="Credenciales incorrectas"
        )
    
    access_token = secrets.token_urlsafe(32)
    expiration = (datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_LIFETIME_MINUTES))

    db.create_session(token_hash(access_token), user["id"], expiration.replace(tzinfo=None))
    response.headers["Cache-Control"] = "no-store" # Checkear
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "expires_in": config.TOKEN_LIFETIME_MINUTES * 60
    }


@app.post("/introspect", dependencies=[Depends(verify_gateway)])
def introspect(request: IntrospectionRequest):
    session = db.get_session(token_hash(request.token))

    if session is None:
        return {"active": False}
    
    return {
        "active": True, 
        "user_id": str(session["user_id"]),
        "username": session["username"],
        "roles": [session["role"]], 
        "expires_at": session["expires_at"].replace(tzinfo=timezone.utc).isoformat()
    }


@app.post("/logout", dependencies=[Depends(verify_gateway)])
def logout(request: IntrospectionRequest):
    db.delete_session(token_hash(request.token))
    return {"message": "Sesión finalizada"}


@app.post("/register", dependencies=[Depends(verify_gateway)], status_code=201)
def register(body: RegistrationRequest):
    try:
        return db.register(body.username, hash_password(body.password))
    
    except IntegrityError:
        raise HTTPException(
            status_code=409, 
            detail="Nombre de usuario ya registrado"
        )


# ===== AUTH USERS =====
@app.get("/admin/users", dependencies=[Depends(require_admin)])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    return db.list_users(skip, limit)


@app.post("/admin/users", dependencies=[Depends(require_admin)], status_code=201)
def create_user(body: UserCreate):
    try:
        password_hash = hash_password(body.password)
        return db.create_admin_user(
            body.username,
            password_hash,
            body.role,
            body.enabled
        )
    except IntegrityError:
        raise HTTPException(409, "Nombre de usuario ya registrado")


@app.get("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def get_user(user_id: int = Path(gt=0)):
    return db.get_public_user(user_id)


@app.put("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def update_user(body: UserUpdate, user_id: int = Path(gt=0)):
    try:
        password_hash = (
            hash_password(body.password)
            if body.password is not None
            else None
        )

        return db.update_user(
            user_id,
            body.username,
            body.role,
            body.enabled,
            password_hash
        )
    except IntegrityError:
        raise HTTPException(409, "Nombre de usuario ya registrado")


@app.delete(
    "/admin/users/{user_id}",
    dependencies=[Depends(require_admin)],
    status_code=204
)
def disable_user(user_id: int = Path(gt=0)):
    db.disable_user(user_id)
    return Response(status_code=204)

# ===== INTERAL COMUNICATION =====
@app.get(
    "/internal/users/{user_id}",
    dependencies=[Depends(verify_clients)]
)
def account_for_profile(user_id: int = Path(gt=0)):
    return db.account_for_profile(user_id)
    

# Middleware
install(app)
