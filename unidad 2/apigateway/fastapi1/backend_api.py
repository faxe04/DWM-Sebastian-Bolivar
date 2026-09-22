from fastapi import FastAPI


app = FastAPI(
    title="Servicio 1",
    description="API ubicada en local host enrutada por API gateway"
)


@app.get("/heath")
def health():
    return {
        "status": "Ok",
        "service": "Backend API"
    }


@app.get("/products")
def products():
    return {
        "products": [
            {"id": 1, "name": "Café Colombia", "price": 7990},
            {"id": 2, "name": "Croissant Clásico", "price": 3500}
        ]
    }


@app.get("/orders")
def orders():
    return {
        "orders": [
            {"id": 10, "status": "paid"},
            {"id": 11, "status": "pending"}
        ]
    }
