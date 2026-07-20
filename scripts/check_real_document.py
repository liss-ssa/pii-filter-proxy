from __future__ import annotations

import argparse
from pathlib import Path

from app.detection.engine import DetectionEngine
from app.parsers.factory import parse_document

MIME_BY_SUFFIX = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    path = Path(args.file)
    mime = MIME_BY_SUFFIX.get(path.suffix.lower())
    if not mime:
        raise SystemExit(f"Unsupported extension: {path.suffix}")
    parsed = parse_document(path.read_bytes(), mime)
    entities = DetectionEngine().detect(parsed.text)
    for entity in entities:
        value = parsed.text[entity.start:entity.end].replace("\n", " ")
        print(f"{entity.entity_type:18} {entity.score:.3f} {value!r} | {entity.reason}")
    print(f"entities={len(entities)} chars={len(parsed.text)}")


if __name__ == "__main__":
    main()
