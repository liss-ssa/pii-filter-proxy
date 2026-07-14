from fastapi import FastAPI
from fastapi.responses import ORJSONResponse,PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST,generate_latest
from app.api.routes import router
from app.config import get_settings
from app.api.routes import engine

settings=get_settings(); app=FastAPI(title=settings.app_name,default_response_class=ORJSONResponse); app.include_router(router)

@app.get("/health/live")
def live(): return {"status":"ok"}

@app.get("/health/ready")
def ready(): return {"status":"ready","device":settings.inference_device,"filter_enabled":settings.pii_filter_enabled,"natasha":engine.ner.status.__dict__,"context_classifier":{"enabled":settings.context_classifier_enabled,"loaded":engine.classifier.loaded,"model_dir":settings.context_model_dir,"error":engine.classifier.error}}

@app.get("/metrics",response_class=PlainTextResponse)
def metrics(): return PlainTextResponse(generate_latest().decode(),media_type=CONTENT_TYPE_LATEST)
