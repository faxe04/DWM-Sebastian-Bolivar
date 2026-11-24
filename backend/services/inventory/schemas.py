from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120, description="Nombre del producto")
    description: str = Field(min_length=1, max_length=1000, description="Descripción del producto")
    category: str = Field(min_length=1, max_length=60, description="Categoría del producto")
    price: StrictInt = Field(gt=0, le=100_000_000, description="Precio en pesos chilenos enteros")
    available: bool = True
    featured: bool = False


class ProductInput(Product):
    stock: StrictInt = Field(ge=0, le=1_000_000, description="Cantidad disponible")


class ProductPublic(Product):
    id: int


class ProductAdmin(ProductPublic):
    stock: int


def row_to_product(row, *, admin=False):
    data = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "price": row["price"],
        "available": bool(row["available"]),
        "featured": bool(row["featured"]),
    }
    if admin:
        return ProductAdmin(**data, stock=row["stock"])
    data["available"] = data["available"] and row["stock"] > 0
    return ProductPublic(**data)


class ReservationItem(BaseModel):
    product_id: StrictInt = Field(gt=0)
    quantity: StrictInt = Field(gt=0, le=100)


class ReservationInput(BaseModel):
    items: list[ReservationItem] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("No repitas productos")
        return self
