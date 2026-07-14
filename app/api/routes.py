import asyncio,time,httpx
from fastapi import APIRouter,File,HTTPException,UploadFile
from app.api.schemas import RedactRequest,RedactResponse,ProxyRequest
from app.config import get_settings
from app.detection.engine import DetectionEngine
from app.anonymization.replacer import replace_entities
from app.parsers.factory import parse_document
from app.security.input_validation import validate_payload
from app.observability.metrics import REQUESTS,LATENCY,ENTITIES,INFLIGHT,REVIEW

router=APIRouter(); settings=get_settings(); engine=DetectionEngine(); semaphore=asyncio.Semaphore(settings.max_concurrent_inference)

async def _process(text,policy):
    started=time.perf_counter()
    
    if not settings.pii_filter_enabled:
        if settings.disabled_policy=="bypass": return RedactResponse(status="ok",text=text,entities=[],processing_ms=0,policy="disabled:bypass")
        raise HTTPException(503,"PII filter disabled")
    try:
        async with asyncio.timeout(settings.queue_timeout_ms/1000): await semaphore.acquire()
    except TimeoutError as exc: raise HTTPException(503,"PII inference queue timeout",headers={"Retry-After":"1"}) from exc
    try:
        INFLIGHT.inc(); entities=await asyncio.to_thread(engine.detect,text)
    finally: INFLIGHT.dec(); semaphore.release()
    
    for e in entities: ENTITIES.labels(e.entity_type).inc()
    certain=[e for e in entities if e.score>=settings.redact_threshold]
    uncertain=[e for e in entities if settings.review_low<=e.score<settings.redact_threshold]
    
    if policy=="mask":
        certain += uncertain
        uncertain = []
    redacted,meta=replace_entities(text,certain); elapsed=(time.perf_counter()-started)*1000
    
    if uncertain and policy=="review":
        REVIEW.inc(); meta += [{"type":e.entity_type,"placeholder":None,"start":e.start,"end":e.end,"score":e.score,"reason":e.reason,"uncertain":True} for e in uncertain]
        return RedactResponse(status="review_required",text=None,entities=meta,processing_ms=elapsed,policy=policy)
    return RedactResponse(status="ok",text=redacted,entities=meta,processing_ms=elapsed,policy=policy)

@router.post("/v1/redact",response_model=RedactResponse)
async def redact(body:RedactRequest):
    policy=body.uncertain_policy or settings.uncertain_policy
    with LATENCY.labels("redact").time(): result=await _process(body.text,policy)
    REQUESTS.labels("redact",result.status).inc(); return result

@router.post("/v1/redact-file",response_model=RedactResponse)
async def redact_file(file:UploadFile=File(...),uncertain_policy:str|None=None):
    ct=(file.content_type or "").split(";")[0]; data=await file.read(settings.max_input_bytes+1); validate_payload(data,ct,settings.max_input_bytes)
    try: parsed=await asyncio.to_thread(parse_document,data,ct)
    except Exception as exc: raise HTTPException(422,f"Document parsing failed: {exc}") from exc
    return await _process(parsed.text,uncertain_policy or settings.uncertain_policy)

@router.post("/v1/proxy/chat")
async def proxy_chat(body:ProxyRequest):
    if not settings.upstream_llm_url: raise HTTPException(503,"UPSTREAM_LLM_URL is not configured")
    result=await _process(body.text,body.uncertain_policy or settings.uncertain_policy)
    if result.status!="ok" or result.text is None:return result
    payload=dict(body.upstream_payload or {}); payload["text"]=result.text
    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client: response=await client.post(settings.upstream_llm_url,json=payload)
    return {"redaction":result.model_dump(),"upstream_status":response.status_code,"upstream_response":response.json()}
