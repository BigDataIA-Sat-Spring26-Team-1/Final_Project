FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies if required and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy only pyproject.toml first to cache dependency installation
COPY pyproject.toml .

# Install dependencies using uv into the system environment to leverage Docker caching
RUN uv pip install --system --no-cache -e .

# Copy application files
COPY app/ ./app/

# Create logs directory
RUN mkdir -p logs

EXPOSE 8000

# Start the uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
