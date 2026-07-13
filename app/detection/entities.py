from dataclasses import dataclass

@dataclass(frozen=True)
class Entity:
    entity_type: str
    start: int
    end: int
    score: float
    reason: str

    @property
    def text_slice(self):
        return slice(self.start, self.end)
