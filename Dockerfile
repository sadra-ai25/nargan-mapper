FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create cache directory
RUN mkdir -p /tmp/nargan_cache

# Expose port
EXPOSE 9004

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9004"]