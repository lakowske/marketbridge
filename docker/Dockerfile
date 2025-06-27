# MarketBridge Combined Server Docker Image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy web content and scripts
COPY web/ ./web/
COPY run_server.py ./
COPY scripts/ ./scripts/

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash marketbridge
RUN chown -R marketbridge:marketbridge /app
USER marketbridge

# Expose ports
EXPOSE 8080 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Default command
CMD ["python", "run_server.py"]
