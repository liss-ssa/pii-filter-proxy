from prometheus_client import Counter, Gauge, Histogram
REQUESTS=Counter("pii_requests_total","Requests",["endpoint","status"])
LATENCY=Histogram("pii_request_duration_seconds","Request latency",["endpoint"])
ENTITIES=Counter("pii_entities_total","Detected entities",["entity_type"])
INFLIGHT=Gauge("pii_inflight_requests","In-flight inference requests")
REVIEW=Counter("pii_review_required_total","Review-required responses")
