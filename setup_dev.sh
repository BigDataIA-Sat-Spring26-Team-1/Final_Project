#!/bin/bash
# CurateAI Development Environment Bootstrapper
# This script ensures Qdrant is running, dependencies are synced, and the backend is ready.

set -e

echo "------------------------------------------------"
echo "CurateAI Development Setup Initiated"
echo "------------------------------------------------"

# 1. Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker Desktop first."
  exit 1
fi

# 2. Spin up Qdrant
echo "[1/3] Booting Qdrant Vector DB..."
if command -v docker-compose &> /dev/null; then
  docker-compose -f infrastructure/docker-compose.yml up -d
else
  docker compose -f infrastructure/docker-compose.yml up -d
fi

# 3. Setup Backend Environment (using uv)
echo "[2/3] Syncing Python dependencies (uv)..."
cd backend
if ! command -v uv &> /dev/null; then
    echo "Warning: uv not found. Installing via pip..."
    pip install uv
fi
uv sync

# 4. Verify Database Connectivity
echo "[3/3] Running Agent Scaffold Verification..."
uv run python tests/verify_scaffolds.py

echo "------------------------------------------------"
echo "SETUP COMPLETE"
echo "------------------------------------------------"
echo "1. Root: Copy .env.example to .env and fill in keys."
echo "2. Run Backend: cd backend && uv run uvicorn app.main:app --reload"
echo "3. Documentation: Read /Temp/Updated_Task_Tracking.md"
echo "------------------------------------------------"
