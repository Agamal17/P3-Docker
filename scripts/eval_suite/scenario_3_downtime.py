import time
import threading
import subprocess
import grpc

def _wait_for_recovery(stop_event, is_recovered_ref, current_status_ref, label, timeout=60):
    """Block until the prober signals recovery or timeout is hit."""
    wait_start = time.time()
    while not stop_event.is_set():
        if is_recovered_ref[0]:
            break
        # If system never went down (e.g. backup kill), detect that after 10s
        if time.time() - wait_start > 10 and current_status_ref[0]:
            print(f"[{label}] System remained healthy — no client-visible downtime.")
            break
        if time.time() - wait_start > timeout:
            elapsed = time.time() - wait_start
            print(f"[{label}] Warning: System did not recover within {timeout}s! (waited {elapsed:.1f}s)")
            break
        time.sleep(0.5)

def _wait_for_pod_ready(pod_name, timeout=120):
    """Wait until a specific K8s pod is ready."""
    subprocess.run(
        ["kubectl", "wait", "--for=condition=ready", f"pod/{pod_name}", f"--timeout={timeout}s"],
        check=False, capture_output=True
    )

def run_downtime_scenario(wrapper):
    print("--- Running Scenario 3: Downtime & Recovery ---")
    
    stop_event = threading.Event()
    results = {"backup_kill": [], "primary_kill": []}
    is_recovered = [False]
    current_status = [True]

    def prober():
        last_status = True
        fail_start = None
        while not stop_event.is_set():
            try:
                wrapper.get_item("bench-item-0", timeout=2)
                if not last_status and fail_start:
                    downtime = time.time() - fail_start
                    results["_active_list"].append(downtime)
                    print(f"[Prober] Recovered! Downtime: {downtime:.2f}s")
                    fail_start = None
                    is_recovered[0] = True
                last_status = True
                current_status[0] = True
            except grpc.RpcError:
                if last_status:
                    fail_start = time.time()
                    print("[Prober] Request failed, starting downtime timer...")
                last_status = False
                current_status[0] = False
            time.sleep(0.1)

    t = threading.Thread(target=prober, daemon=True)
    t.start()
    
    print("Waiting 3s for prober to stabilize...")
    time.sleep(3)

    # ---- Phase 1: Kill a backup node ----
    print("\n=== Phase 1: Killing Backup Node ===")
    results["_active_list"] = results["backup_kill"]
    is_recovered[0] = False

    if wrapper.env_type == "k8s":
        subprocess.run(["kubectl", "delete", "pod", "storage-1", "--grace-period=0", "--force"], check=False)
    else:
        subprocess.run(["docker", "kill", "storage-1"], check=False)
    
    _wait_for_recovery(stop_event, is_recovered, current_status, "Backup Kill", timeout=60)

    # Wait for backup to be fully back before proceeding
    if wrapper.env_type == "k8s":
        print("Waiting for backup pod storage-1 to be recreated and ready...")
        _wait_for_pod_ready("storage-1")
        time.sleep(3)  # extra settle time for controller to re-register it

    # ---- Phase 2: Kill the primary node ----
    print("\n=== Phase 2: Killing Primary Node ===")
    results["_active_list"] = results["primary_kill"]
    is_recovered[0] = False

    if wrapper.env_type == "k8s":
        subprocess.run(["kubectl", "delete", "pod", "storage-0", "--grace-period=0", "--force"], check=False)
    else:
        subprocess.run(["docker", "kill", "storage-0"], check=False)

    _wait_for_recovery(stop_event, is_recovered, current_status, "Primary Kill", timeout=60)

    stop_event.set()
    t.join(timeout=3)

    # ---- Report ----
    print("\n=== Downtime Summary ===")
    if results["backup_kill"]:
        for i, dt in enumerate(results["backup_kill"]):
            print(f"  Backup Kill Event {i+1}: {dt:.2f}s")
    else:
        print("  Backup Kill: No client-visible downtime (reads route to primary)")

    if results["primary_kill"]:
        for i, dt in enumerate(results["primary_kill"]):
            print(f"  Primary Kill Event {i+1}: {dt:.2f}s")
    else:
        print("  Primary Kill: No downtime recorded (system may not have recovered)")
    print()
