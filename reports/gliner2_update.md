# GLiNER2-PII update

Implemented Variant B with field-aware safety policy.

- GLiNER2-PII is the default lazy local NER backend.
- Natasha is disabled by default and retained only as an optional baseline/fallback.
- Added structured-field context for OGRN, KPP, INN, KTRU, OKPD2 and contract identifiers.
- Fixed OGRN -> BANK_CARD false positive.
- Fixed KTRU -> IP_ADDRESS false positive.
- Fixed tax-registration/publication dates -> DATE_OF_BIRTH/DATE false positives.
- Restricted IP masking to explicit network context.
- Restricted fail-safe masking to plausible physical-person scope.
- Organization contact data remains visible by default.
- Added real-document regression tests and model warm-up/download script.

Local rule-aligned pipeline result: 14 tests passed. The GLiNER2 model weights were not available in the build environment, so model-level Russian quality must be evaluated after local download.
