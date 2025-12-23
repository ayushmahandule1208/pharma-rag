# Dockerfile for PharmaRAG Backend
# Compatible with Hugging Face Spaces (port 7860) and Render (port 8000)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories with proper permissions
RUN mkdir -p data/raw data/processed data/faiss_index && \
    chmod -R 777 data

# Expose ports (7860 for HF Spaces, 8000 for Render)
EXPOSE 7860 8000

# Default: Run HF Spaces compatible server
# Override with CMD in platform settings if needed
CMD ["python", "app.py"]

