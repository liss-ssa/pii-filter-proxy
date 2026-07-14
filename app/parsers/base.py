from dataclasses import dataclass

@dataclass
class ParsedDocument:
    text: str
    content_type: str
