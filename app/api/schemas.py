from typing import Any, Literal
from pydantic import BaseModel, Field

class RedactRequest(BaseModel):
    text:str=Field(min_length=1,max_length=50000)
    content_type:Literal["text/plain","text/markdown","text/html"]="text/plain"
    uncertain_policy:Literal["pass","review"]|None=None

class ProxyRequest(RedactRequest): upstream_payload:dict[str,Any]|None=None

class RedactResponse(BaseModel):
    status:Literal["ok","review_required","blocked"]
    text:str|None
    entities:list[dict[str,Any]]
    processing_ms:float
    policy:str
