from collections import defaultdict
from app.detection.entities import Entity

def replace_entities(text: str, entities: list[Entity]):
    counters=defaultdict(int); value_map={}; metadata=[]; replacements=[]
    for e in sorted(entities,key=lambda x:(x.start,x.end)):
        value=text[e.start:e.end]
        key=(e.entity_type,value.casefold())
        if key not in value_map:
            counters[e.entity_type]+=1
            value_map[key]=f"[{e.entity_type}_{counters[e.entity_type]}]"
        ph=value_map[key]
        replacements.append((e.start,e.end,ph))
        metadata.append({"type":e.entity_type,"placeholder":ph,"start":e.start,"end":e.end,"score":e.score,"reason":e.reason})
    result=text
    for s,e,ph in reversed(replacements): result=result[:s]+ph+result[e:]
    return result, metadata
