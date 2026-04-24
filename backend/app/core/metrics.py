from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry

REGISTRY = CollectorRegistry()

LLM_REQUESTS_TOTAL = Counter(
    "curateai_llm_requests_total",
    "Total number of LLM completion requests",
    ["model", "status"],
    registry=REGISTRY
)

LLM_TOKENS_TOTAL = Counter(
    "curateai_llm_tokens_total",
    "Total tokens consumed by LLM calls",
    ["model", "token_type"], 
    registry=REGISTRY
)

LLM_COST_TOTAL = Counter(
    "curateai_llm_cost_total",
    "Estimated total cost of LLM calls in USD",
    ["model"],
    registry=REGISTRY
)

NEWSLETTER_REJECTIONS_TOTAL = Counter(
    "curateai_newsletter_rejections_total",
    "Total times the Editor node rejected a draft and triggered revision",
    ["user_id"], 
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    "curateai_http_request_duration_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "endpoint", "status"],
    registry=REGISTRY
)

LANGGRAPH_NODE_LATENCY = Histogram(
    "curateai_langgraph_node_latency_seconds",
    "Execution time of specific LangGraph agent nodes",
    ["node_name"],
    registry=REGISTRY
)

ACTIVE_AGENT_SESSIONS = Gauge(
    "curateai_active_agent_sessions",
    "Number of LangGraph workflows currently in-flight",
    registry=REGISTRY
)

DAG_TRIGGERS_TOTAL = Counter(
    "curateai_dag_triggers_total",
    "DAG trigger attempts from the backend to Airflow",
    ["dag_id", "status"],  
    registry=REGISTRY,
)

DAG_TRIGGER_LATENCY = Histogram(
    "curateai_dag_trigger_latency_seconds",
    "Time spent calling the Airflow REST API to fire a DAG",
    ["dag_id"],
    registry=REGISTRY,
)