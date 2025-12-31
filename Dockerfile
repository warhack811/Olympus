# Base Image
FROM python:3.11-slim

# Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

# Work Directory
WORKDIR /app

# Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
COPY requirements.txt .
RUN pip install uv && uv pip install --system --no-cache -r requirements.txt

# Copy Project Code
COPY . .

# Expose Port
EXPOSE 8000

# Entrypoint
CMD ["uvicorn", "core_v2.main:app", "--host", "0.0.0.0", "--port", "8000"]
