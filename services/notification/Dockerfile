# Notification Service Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    celery==5.3.4 \
    redis==5.0.1 \
    amqp==5.2.0 \
    pydantic[email]==2.5.0

COPY src/ ./src/

EXPOSE 8002

# Default command runs the API
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
