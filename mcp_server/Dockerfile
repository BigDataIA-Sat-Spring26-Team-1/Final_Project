FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy pyproject.toml first for caching
# We point to the backend pyproject because that's where the core logic dependencies are
COPY backend/pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system --no-cache -e .

# Copy application files (backend code)
COPY backend/app/ ./app/

# Create logs directory
RUN mkdir -p logs

EXPOSE 8001

# Run the MCP server standalone
# Note: Ensure the build context is set to the root folder
CMD ["python", "app/core/mcp_server.py"]
