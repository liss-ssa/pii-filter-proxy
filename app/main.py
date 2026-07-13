from fastapi import FastAPI
from fastapi.responses import ORJSONResponse,PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST,generate_latest
from app.api.routes import router
from app.config import get_settings

settings=get_settings(); app=FastAPI(title=settings.app_name,default_response_class=ORJSONResponse); app.include_router(router)
@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/health/ready")
def ready(): return {"status":"ready","device":settings.inference_device,"filter_enabled":settings.pii_filter_enabled}
@app.get("/metrics",response_class=PlainTextResponse)
def metrics(): return PlainTextResponse(generate_latest().decode(),media_type=CONTENT_TYPE_LATEST)
