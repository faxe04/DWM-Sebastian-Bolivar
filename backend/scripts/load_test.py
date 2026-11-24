"""Carga reproducible de lectura. Guarda mediciones, nunca tokens ni respuestas."""
import argparse
import concurrent.futures
import json
import math
import os
import ssl
import time
import subprocess
import threading
from pathlib import Path
import httpx

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--path", default="/api/v1/products?limit=20")
    parser.add_argument("--docker-stats", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.requests <= 5000 or not 1 <= args.concurrency <= 50:
        parser.error("Usa 1–5000 solicitudes y 1–50 trabajadores")
    ca = os.getenv("API_CA_FILE")
    verify = ssl.create_default_context(cafile=ca) if ca else True
    headers = {}
    token = os.getenv("API_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    samples = []
    done = threading.Event()
    def sample_resources():
        while not done.is_set():
            try:
                result = subprocess.run(["docker","stats","--no-stream","--format","{{json .}}"], capture_output=True, text=True, timeout=10)
                rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                samples.append({"seconds":round(time.time(),2),"containers":[row for row in rows if row.get("Name","").startswith("aroma-backend-dev-")]})
            except (OSError, subprocess.TimeoutExpired, ValueError):
                samples.append({"unavailable":True})
                break
            done.wait(1)
    sampler = threading.Thread(target=sample_resources, daemon=True)
    if args.docker_stats:
        sampler.start()
    with httpx.Client(base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
                      timeout=10, verify=verify, headers=headers) as client:
        def one(_):
            started = time.perf_counter()
            try:
                response = client.get(args.path)
                status, size = response.status_code, len(response.content)
            except httpx.RequestError:
                status, size = 0, 0
            return time.perf_counter()-started, status, size
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(one, range(args.requests)))
        duration = time.perf_counter()-start
    done.set()
    if args.docker_stats:
        sampler.join(timeout=12)
    latencies = sorted(row[0] for row in results)
    report = {"scenario":"carga sintética, no usuarios reales", "requests":args.requests,
        "concurrency":args.concurrency, "duration_seconds":round(duration,3),
        "p95_ms":round(latencies[math.ceil(.95*len(latencies))-1]*1000,2),
        "throughput_requests_second":round(len(results)/duration,2),
        "errors":sum(status != 200 for _,status,_ in results),
        "average_response_bytes":round(sum(size for _,_,size in results)/len(results)),
        "cpu_memory_samples":samples,
        "target_p95_ms":1000}
    output = Path(__file__).resolve().parents[1] / ".runtime" / "pruebas"
    output.mkdir(parents=True, exist_ok=True)
    (output / "load-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
