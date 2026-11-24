from typing import Optional
from fastapi import Header, Depends, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from mysql.connector import Error as DatabaseError
from . import db
from .schemas import ProductAdmin, ProductInput, ProductPublic, ReservationInput, row_to_product
from .security import require_admin, verify_gateway, check_secret

from backend.request_logging import install


app = FastAPI(
    title="Servicio Inventario - Aroma & Café",
    description="Catálogo privado de la cafetería",
    docs_url=None, 
    redoc_url=None, 
    openapi_url=None,
)


@app.exception_handler(DatabaseError)
async def database_error(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=503, content={"detail": "Persistencia no disponible"})


# ===== System =====
@app.get("/health", tags=["sistema"], dependencies=[Depends(verify_gateway)])
def health():
    return {"status": "ok", "service": "inventory"}


# ===== Public Inventory =====
@app.get("/products", response_model=list[ProductPublic], tags=["productos"], dependencies=[Depends(verify_gateway)])
def list_products(
    q: Optional[str] = Query(None, min_length=1, max_length=120, description="Texto contenido en el nombre"),
    skip: int = Query(0, ge=0, description="Cantidad de registros a omitir"),
    limit: int = Query(50, ge=1, le=100, description="Límite de registros"),
    category: Optional[str] = Query(None, min_length=1, max_length=60),
    available: Optional[bool] = None,
    featured: Optional[bool] = None,
):
    rows = db.list_products(q=q, skip=skip, limit=limit, category=category, available=available, featured=featured)
    return [row_to_product(row) for row in rows]


@app.get("/products/{product_id}", response_model=ProductPublic, tags=["productos"], dependencies=[Depends(verify_gateway)])
def get_product(product_id: int = Path(gt=0)):
    row = db.get_product(product_id)
    if row is None:
        raise HTTPException(404, "Producto no encontrado")
    return row_to_product(row)


# ===== Administration =====
@app.get("/admin/products", response_model=list[ProductAdmin], dependencies=[Depends(require_admin)])
def list_admin_products(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    return [row_to_product(row, admin=True) for row in db.list_products(skip=skip, limit=limit)]


@app.post("/admin/products", response_model=ProductAdmin, status_code=201, dependencies=[Depends(require_admin)])
def create_product(product: ProductInput):
    row = db.create_product(product.model_dump())
    return row_to_product(row, admin=True)


@app.put("/admin/products/{product_id}", response_model=ProductAdmin, dependencies=[Depends(require_admin)])
def update_product(product: ProductInput, product_id: int = Path(gt=0)):
    row = db.update_product(product_id, product.model_dump())
    if row is None:
        raise HTTPException(404, "Producto no encontrado")
    return row_to_product(row, admin=True)


@app.delete("/admin/products/{product_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_product(product_id: int = Path(gt=0)):
    if not db.delete_product(product_id):
        raise HTTPException(404, "Producto no encontrado")
    return Response(status_code=204)


@app.post("/internal/reservations/{order_id}")
def reserve(body: ReservationInput, order_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret)
    return db.reserve(order_id, [item.model_dump() for item in body.items])


@app.delete("/internal/reservations/{order_id}", status_code=204)
def release(order_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret)
    db.release(order_id)
    return Response(status_code=204)


# Middleware
install(app)
