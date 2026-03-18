# Job Matching Service Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for MySQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    uvloop==0.19.0 \
    aiomysql==0.2.0 \
    redis==5.0.1 \
    pydantic==2.5.0

COPY src/ ./src/

EXPOSE 8001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--loop", "uvloop"]
