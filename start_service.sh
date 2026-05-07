#!/usr/bin/env bash
set -euo pipefail

echo "Building Docker image marketplace:latest..."
docker build -t marketplace:latest .

echo "Ensuring docker network marketplace_net exists..."
if ! docker network inspect marketplace_net >/dev/null 2>&1; then
  docker network create marketplace_net
fi

echo "Starting controller via docker-compose..."
docker-compose up -d --build controller

echo "Waiting for controller on localhost:50050..."
for i in $(seq 1 60); do
  if timeout 1 bash -c 'cat < /dev/tcp/localhost/50050' >/dev/null 2>&1; then
    echo "Controller is up"
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for controller" >&2
exit 1
