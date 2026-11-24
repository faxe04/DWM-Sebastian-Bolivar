FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home appuser
COPY __init__.py /app/backend/__init__.py
COPY request_logging.py /app/backend/request_logging.py
COPY services /app/backend/services
COPY gateway /app/backend/gateway
COPY tests /app/backend/tests
COPY auth /app/backend/auth
COPY scripts /app/backend/scripts
COPY infrastructure /app/backend/infrastructure
USER appuser
CMD ["uvicorn", "backend.services.inventory.main:app", "--host", "0.0.0.0", "--port", "9000"]
