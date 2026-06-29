# Stage 1: Build/dependency layer
FROM python:3.10-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libcairo2-dev libpango1.0-dev \
    libgdk-pixbuf-2.0-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production runtime
FROM python:3.10-slim AS production

WORKDIR /app

# Only runtime system deps for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy only the installed packages from builder
COPY --from=builder /install /usr/local

COPY . .

# Run as non-root user for security
RUN useradd -r -s /bin/false arthai
RUN chown -R arthai:arthai /app
USER arthai

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2"]
