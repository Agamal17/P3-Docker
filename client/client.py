import sys
import os
import grpc

import kv_pb2
import kv_pb2_grpc

# If running in devcontainer use host.docker.internal
# If running on host machine use localhost
TARGET = os.environ.get("TARGET",  "localhost:50051")
# TARGET = "host.docker.internal:50051"
# TARGET = "localhost:50051"

def main():
    if len(sys.argv) < 3:
        print("put <key> <value>")
        print("get <key>")
        return
    
    key=sys.argv[2]
    value=sys.argv[3]
    
    with grpc.insecure_channel(TARGET) as channel:
        stub = kv_pb2_grpc.FrontendServiceStub(channel)
        response = stub.Put(kv_pb2.PutRequest(key=key, value=value))
        print({"key": key, "ok": response.ok, "frontend_pod": response.pod})



if __name__ == "__main__":
    main()
