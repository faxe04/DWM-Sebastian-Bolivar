import json
import logging
import re
import time
import uuid
from contextvars import ContextVar

# Permite que una llamada HTTP interna conserve el identificador
# ContextVar separa solicitudes concurrentes; no es una variable compartida entre clientes
REQUEST_ID = ContextVar("request_id", default="")

def install(app):
    @app.middleware("http")
    async def log_request(request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if re.fullmatch(r"[a-zA-Z0-9-]{1,64}", incoming) else str(uuid.uuid4())
        request.state.request_id = request_id
        token = REQUEST_ID.set(request_id)
        started = time.monotonic()

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            route = request.scope.get("route")
            # Solo ruta/resultado/tiempo. Nunca cuerpos, tokens ni contraseñas
            logging.getLogger("uvicorn.error").info(json.dumps({
                "request_id": request_id,
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }))
            return response
        
        finally:
            REQUEST_ID.reset(token)
