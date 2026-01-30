"""
Background job to parse Traefik access logs and extract metrics
"""
from datetime import datetime
import asyncio
import json
import re
import logging
from collections import defaultdict
from database import app_metrics_collection, app_errors_collection
from config import APP_DOMAIN, k8s_core_v1

logger = logging.getLogger(__name__)

# How often to aggregate and store metrics (seconds)
AGGREGATION_INTERVAL = 60

# Traefik namespace and label selector
TRAEFIK_NAMESPACE = "traefik"
TRAEFIK_LABEL_SELECTOR = "app.kubernetes.io/name=traefik"

# Pattern to extract app_id from hostname: app-{app_id}.{domain}
APP_HOST_PATTERN = re.compile(r'^app-([a-z0-9]+)\.' + re.escape(APP_DOMAIN) + '$')


class MetricsAggregator:
    """Aggregates metrics per app over a time window"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all counters"""
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.response_times = defaultdict(list)
        self.errors = []  # Individual error events
    
    def add_request(self, app_id: str, status_code: int, duration_ms: float, 
                    request_path: str = None, request_method: str = None):
        """Record a request for an app"""
        self.request_counts[app_id] += 1
        self.response_times[app_id].append(duration_ms)
        
        # Track errors (4xx and 5xx)
        if status_code >= 400:
            self.error_counts[app_id] += 1
            self.errors.append({
                "app_id": app_id,
                "timestamp": datetime.utcnow(),
                "status_code": status_code,
                "request_path": request_path,
                "request_method": request_method,
                "error_type": "client_error" if status_code < 500 else "server_error"
            })
    
    def get_metrics(self) -> list:
        """Get aggregated metrics for all apps"""
        metrics = []
        timestamp = datetime.utcnow()
        
        for app_id in self.request_counts:
            response_times = self.response_times[app_id]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            metrics.append({
                "app_id": app_id,
                "timestamp": timestamp,
                "request_count": self.request_counts[app_id],
                "error_count": self.error_counts[app_id],
                "avg_response_time_ms": round(avg_response_time, 2),
                "min_response_time_ms": round(min(response_times), 2) if response_times else 0,
                "max_response_time_ms": round(max(response_times), 2) if response_times else 0
            })
        
        return metrics
    
    def get_errors(self) -> list:
        """Get individual error events"""
        return self.errors


def parse_traefik_log_line(line: str) -> dict:
    """
    Parse a Traefik JSON access log line.
    Returns parsed data or None if not parseable/not relevant.
    """
    try:
        log_entry = json.loads(line)
    except json.JSONDecodeError:
        return None
    
    # Extract relevant fields from Traefik access log
    # Traefik JSON format includes: RequestHost, RequestMethod, RequestPath, 
    # OriginStatus, Duration, etc.
    
    request_host = log_entry.get("RequestHost", "")
    
    # Check if this is a user app request
    match = APP_HOST_PATTERN.match(request_host)
    if not match:
        return None  # Not a user app request
    
    app_id = match.group(1)
    
    # Extract metrics
    status_code = log_entry.get("OriginStatus", 0)
    
    # Duration is in nanoseconds in Traefik logs
    duration_ns = log_entry.get("Duration", 0)
    duration_ms = duration_ns / 1_000_000 if duration_ns else 0
    
    return {
        "app_id": app_id,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "request_path": log_entry.get("RequestPath", "/"),
        "request_method": log_entry.get("RequestMethod", "GET"),
        "user_agent": log_entry.get("request_User-Agent", ""),
        "timestamp": log_entry.get("time", "")
    }


async def get_traefik_pod_name() -> str:
    """Get the name of a Traefik pod"""
    if not k8s_core_v1:
        logger.warning("Kubernetes client not available, cannot get Traefik pod")
        return None
    
    try:
        pods = k8s_core_v1.list_namespaced_pod(
            namespace=TRAEFIK_NAMESPACE,
            label_selector=TRAEFIK_LABEL_SELECTOR
        )
        
        for pod in pods.items:
            if pod.status.phase == "Running":
                return pod.metadata.name
        
        logger.warning("No running Traefik pod found")
        return None
    except Exception as e:
        logger.error(f"Error getting Traefik pod: {e}")
        return None


async def stream_traefik_logs(aggregator: MetricsAggregator, stop_event: asyncio.Event):
    """
    Stream and parse Traefik access logs using Kubernetes API.
    """
    if not k8s_core_v1:
        logger.warning("Kubernetes client not available, log parsing disabled")
        return
    
    pod_name = await get_traefik_pod_name()
    if not pod_name:
        logger.warning("Could not find Traefik pod, log parsing disabled")
        return
    
    logger.info(f"Starting to stream logs from Traefik pod: {pod_name}")
    
    try:
        # Use the Kubernetes Python client to stream logs
        # This runs in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        def read_logs():
            """Read logs synchronously (runs in thread pool)"""
            try:
                # Stream logs with follow=True
                log_stream = k8s_core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=TRAEFIK_NAMESPACE,
                    follow=True,
                    tail_lines=100,  # Start with last 100 lines
                    _preload_content=False
                )
                
                for line in log_stream:
                    if stop_event.is_set():
                        break
                    
                    if isinstance(line, bytes):
                        line = line.decode('utf-8', errors='ignore')
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    parsed = parse_traefik_log_line(line)
                    if parsed:
                        aggregator.add_request(
                            app_id=parsed["app_id"],
                            status_code=parsed["status_code"],
                            duration_ms=parsed["duration_ms"],
                            request_path=parsed["request_path"],
                            request_method=parsed["request_method"]
                        )
            except Exception as e:
                logger.error(f"Error reading Traefik logs: {e}")
        
        # Run log reading in a thread pool
        await loop.run_in_executor(None, read_logs)
        
    except Exception as e:
        logger.error(f"Error streaming Traefik logs: {e}")


async def store_metrics(aggregator: MetricsAggregator):
    """Store aggregated metrics and errors to MongoDB"""
    metrics = aggregator.get_metrics()
    errors = aggregator.get_errors()
    
    if metrics:
        try:
            await app_metrics_collection.insert_many(metrics)
            logger.debug(f"Stored {len(metrics)} metrics documents")
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    if errors:
        try:
            await app_errors_collection.insert_many(errors)
            logger.debug(f"Stored {len(errors)} error documents")
        except Exception as e:
            logger.error(f"Error storing errors: {e}")


async def run_log_parser_loop():
    """
    Main loop that coordinates log streaming and metric aggregation.
    """
    logger.info(f"Starting log parser loop (aggregation interval: {AGGREGATION_INTERVAL}s)")
    
    aggregator = MetricsAggregator()
    stop_event = asyncio.Event()
    
    # Start log streaming in background
    stream_task = asyncio.create_task(stream_traefik_logs(aggregator, stop_event))
    
    try:
        while True:
            # Wait for aggregation interval
            await asyncio.sleep(AGGREGATION_INTERVAL)
            
            # Store current metrics
            await store_metrics(aggregator)
            
            # Reset aggregator for next interval
            aggregator.reset()
            
    except asyncio.CancelledError:
        logger.info("Log parser loop cancelled")
        stop_event.set()
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_log_parser_loop())
