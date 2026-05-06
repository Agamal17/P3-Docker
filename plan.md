3B. Evaluation Plan

1. Fault Tolerance Recovery Time
Metric: Time-to-Recovery (TTR).

Method: Manually kill a Kubernetes Pod (the Primary replica) while a client is loop-requesting the product list. I will measure how many seconds of downtime occur before a Backup is promoted and the system becomes responsive again.


2. Scaling Throughput under Load
Metric: Requests Per Second (RPS) and Latency.

Method: Use a simple multi-threaded Python script to simulate 10–50 concurrent clients. I will monitor the Kubernetes Horizontal Pod Autoscaler (HPA) to verify that as CPU/Request load increases, the number of Service Layer pods increases to maintain low latency.


3. Consistency Verification
Metric: Conflict rate or Stale Read count.

Method: Run two simultaneous clients attempting to buy the very last item in stock. A successful evaluation will show that despite replication, the system correctly processes only one order and rejects the second (demonstrating proper synchronization across replicas).
