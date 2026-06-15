from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from api.config import Settings

_provider: TracerProvider | None = None

def configure_tracing() -> None:
    """Wire OpenTelemetry to App Insights on FastAPI startup."""
    global _provider
    settings = Settings()
    if not settings.applicationinsights_connection_string:
        return
    try:
        resource = Resource.create({SERVICE_NAME: "meridian-api"})
        exporter = AzureMonitorTraceExporter(
            connection_string=settings.applicationinsights_connection_string
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _provider = provider
    except Exception:
        pass

def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
