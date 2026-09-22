from fastapi import FastAPI


app = FastAPI(
    title="Servicio 2",
    description="API ubicada en local host enrutada por API gateway"
)


@app.get("/heath")
def health():
    return {
        "status": "Ok",
        "service": "Backend API"
    }


@app.get("/productos")
def products():
    return {
        "products": [
            {"id": 1, "nombre": "Café Colombia", "precio": 7990},
            {"id": 2, "nombre": "Croissant Clásico", "precio": 3500}
        ]
    }


@app.get("/ordenes")
def orders():
    return {
        "orders": [
            {"id": 10, "status": "paid"},
            {"id": 11, "status": "pending"}
        ]
    }
