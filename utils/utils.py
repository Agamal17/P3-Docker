import time

import docker
import docker.errors
import grpc
from market_pb2 import *
from utils.config import DOCKER_IMAGE, DOCKER_NETWORK, NODE_PORT


def wait_for_grpc_target(target: str, retry_seconds: float = 0.5) -> None:
    while True:
        try:
            with grpc.insecure_channel(target) as channel:
                grpc.channel_ready_future(channel).result(timeout=1)
            return
        except grpc.FutureTimeoutError:
            time.sleep(retry_seconds)
        except grpc.RpcError:
            time.sleep(retry_seconds)

def create_service_node(node_num: int, storage_targets: list) -> str:
    client = docker.from_env()
    name: str = f"service-{node_num}"
    target: str = f"{name}:{NODE_PORT}"

    try:
        client.containers.get(name).remove(force=True)
    except docker.errors.NotFound:
        pass

    client.containers.run(
        DOCKER_IMAGE,
        name=name,
        hostname=name,
        network=DOCKER_NETWORK,
        detach=True,
        working_dir="/app",
        command=["python", "-u", "service/service.py"],
        environment={
            "CONTROLLER_ADDR": "controller:50050",
            "NODE_ID": name,
            "PORT": str(NODE_PORT),
            "PYTHONPATH": "/app:/app/proto/src",
            "PYTHONUNBUFFERED": "1",
            "STORAGE_TARGETS": ",".join(storage_targets),
        },
    )
    wait_for_grpc_target(target)
    return target


def create_storage_node(node_num: int, storage_targets: list) -> str:
    client = docker.from_env()
    name: str = f"storage-{node_num}"
    target: str = f"{name}:{NODE_PORT}"

    try:
        client.containers.get(name).remove(force=True)
    except docker.errors.NotFound:
        pass

    client.containers.run(
        DOCKER_IMAGE,
        name=name,
        hostname=name,
        network=DOCKER_NETWORK,
        detach=True,
        working_dir="/app",
        command=["python", "-u", "storage/storage.py"],
        environment={
            "CONTROLLER_ADDR": "controller:50050",
            "NODE_ID": name,
            "PORT": str(NODE_PORT),
            "PYTHONPATH": "/app:/app/proto/src",
            "PYTHONUNBUFFERED": "1",
            "STORAGE_TARGETS": ",".join(storage_targets),
        },
    )
    wait_for_grpc_target(target)
    return target
