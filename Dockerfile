# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r chainlit && useradd -r -g chainlit chainlit \
    && mkdir -p /home/chainlit \
    && chown chainlit:chainlit /home/chainlit \
    && chown chainlit:chainlit /app

# Install Python dependencies
COPY --chown=chainlit:chainlit requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY --chown=chainlit:chainlit . .

# Switch to non-root user
USER chainlit

# Expose the port Chainlit runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Create a script to initialize Chainlit and start the application
RUN echo '#!/bin/sh\n\
chainlit init\n\
exec chainlit run app.py --host 0.0.0.0 --port "${PORT:-8000}" --headless\n\
' > /app/start.sh && chmod +x /app/start.sh

# Command to run the application
CMD ["/bin/sh", "/app/start.sh"] 