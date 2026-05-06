#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python -m grpc_tools.protoc -I "$ROOT/proto" --python_out="$ROOT/proto/src" --pyi_out="$ROOT/proto/src" --grpc_python_out="$ROOT/proto/src" "$ROOT/proto/market.proto"
touch "$ROOT/proto/src/__init__.py"
echo "Generated proto/src"
