import subprocess
import time
from .scenario_1_throughput import run_throughput_scenario

def run_scaling_scenario(wrapper):
    print("--- Running Scenario 2: Kubernetes Scaling ---")
    
    if wrapper.env_type != "k8s":
        print("Skipping scaling scenario for non-k8s environment as requested.")
        return

    print("Baseline Test (Current Replicas):")
    baseline_rps = run_throughput_scenario(wrapper, workers=20, duration=10)

    print("Scaling K8s deployment frontend to 3 replicas...")
    subprocess.run(["kubectl", "scale", "deployment/frontend", "--replicas=3"], check=True)
    
    print("Waiting for pods to be ready...")
    time.sleep(5)
    subprocess.run(["kubectl", "wait", "--for=condition=ready", "pod", "-l", "app=frontend", "--timeout=60s"], check=True)

    print("Scaled Test (3 Replicas):")
    # Need to wait a moment for internal DNS/load balancers to register the new endpoints
    time.sleep(5) 
    scaled_rps = run_throughput_scenario(wrapper, workers=50, duration=10)

    print(f"Scaling Results: Baseline={baseline_rps:.2f} rps, Scaled={scaled_rps:.2f} rps")
    
    # Reset back to 1 for subsequent tests
    subprocess.run(["kubectl", "scale", "deployment/frontend", "--replicas=1"], check=True)
    subprocess.run(["kubectl", "wait", "--for=condition=ready", "pod", "-l", "app=frontend", "--timeout=60s"], check=True)
