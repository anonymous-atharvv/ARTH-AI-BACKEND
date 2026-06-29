# Use a lightweight python image
FROM python:3.10-slim

# Install system dependencies for WeasyPrint (PDF engine) and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    media-types \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libglib2.0-0 \
    libopenjp2-7-dev \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files to container
COPY . .

# Expose port 8000
EXPOSE 8000

# Start script
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
