# Use the slim version of Python to keep image size small
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed to compile gRPC tools[cite: 2]
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install gRPC and other Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code and generated gRPC files
COPY . .

# Ensure Python output (logs) is sent straight to the terminal[cite: 2]
ENV PYTHONUNBUFFERED=1

RUN python -m grpc_tools.protoc -I /app/proto --python_out=/app/proto/src --pyi_out=/app/proto/src --grpc_python_out=/app/proto/src /app/proto/market.proto

ENV PYTHONPATH=/app:/app/proto/src