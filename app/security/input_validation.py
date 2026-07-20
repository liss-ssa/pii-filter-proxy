from fastapi import HTTPException
ALLOWED={"text/plain","text/markdown","text/html","application/pdf","application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
def validate_payload(data:bytes,content_type:str,max_bytes:int):
    if len(data)>max_bytes: raise HTTPException(413,"File is too large")
    if content_type not in ALLOWED: raise HTTPException(415,f"Unsupported content type: {content_type}")
    if not data: raise HTTPException(422,"Empty document")
