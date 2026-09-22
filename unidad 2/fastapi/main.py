import os

from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from contextlib import asynccontextmanager

from dotenv import load_dotenv


load_dotenv()

# === Configuracion Data Base ===
MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME")
COLL_NAME = "items"
API_VERSION = "1.1.0"

if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL no esta definido")

if not DB_NAME:
    raise RuntimeError("DB_NAME no esta definido")

client: AsyncIOMotorClient | None = None
db = None
coll = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db, coll
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    coll = db[COLL_NAME]
    yield
    client.close()

app = FastAPI(title="FastAPI Cafeteria", version=API_VERSION, lifespan=lifespan)

class Item(BaseModel):
    nombre: str = Field(min_length=1, description="Nombre del producto")
    descripcion: str = Field(min_length=1, description="Descripción del producto")
    precio: float = Field(gt=0, description="Precio > 0")
    tags: List[str] = Field(default_factory=list)
    activo: bool = True

class ItemIn(BaseModel):
    nombre: str = Field(min_length=1, description="Nombre del producto")
    descripcion: str = Field(min_length=1, description="Descripción del producto")
    precio: float = Field(gt=0, description="Precio > 0")
    tags: List[str] = Field(default_factory=list)
    activo: bool = True

class ItemOut(Item):
    id: str

def doc_to_itemout(doc) -> ItemOut:
    return ItemOut(
        id = str(doc["_id"]),
        nombre = doc["nombre"],
        descripcion = doc["descripcion"],
        precio = doc["precio"],
        tags = doc.get("tags", []),
        activo = doc.get("activo", True)
    )


# === EndPoints ===
@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}


@app.get("/items", response_model=List[ItemOut], tags=["items"])
async def listar_items(
    q: Optional[str] = Query(None, description="Filtro por nombre que contenga q"),
    skip: int = Query(0, ge=0, description="Cantidad de registros a omitir"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros a mostrar"),
):
    query = {}
    if q:
        query["nombre"] = {"$regex": q, "$options": "i"}

    cursor = coll.find(query).skip(skip).limit(limit)
    items: List[ItemOut] = []

    async for doc in cursor:
        items.append(doc_to_itemout(doc))
    return items


@app.post("/items", response_model=ItemOut, status_code=201, tags=["items"])
async def create_item(item: ItemIn):
    res = await coll.insert_one(item.model_dump())
    doc = await coll.find_one({"_id": res.inserted_id})
    return doc_to_itemout(doc)


@app.get("/items/{item_id}", response_model=ItemOut, status_code=200, tags=["items"])
async def get_item(item_id: str):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(400, "ID invalido")
    
    doc = await coll.find_one({"_id": ObjectId(item_id)})

    if not doc:
        raise HTTPException(404, "Item no encontrado")

    return doc_to_itemout(doc)


@app.put("/items/{item_id}", response_model=ItemOut, status_code=200, tags=["items"])
async def update_item(item_id: str, item: ItemIn):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(400, "ID invalido")

    res = await coll.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": item.model_dump()}
    )

    if res.matched_count == 0:
        raise HTTPException(404, "Item no encontrado")
    doc = await coll.find_one({"_id": ObjectId(item_id)})
    return doc_to_itemout(doc)


@app.delete("/items/{item_id}", status_code=204, tags=["items"])
async def delete_item(item_id: str):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(400, "ID invalido")

    res = await coll.delete_one({"_id": ObjectId(item_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Item no encontrado")
    
    return None
