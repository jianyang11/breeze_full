# Private machine-tool v3 — S-C API amendment 1

**Frozen:** 2026-07-14, after the original S-C smoke and before any additional request.

## Observed transport result

The original three-request smoke received HTTP `200` for each class, but all
three were counted as `error:JSONDecodeError` by the inherited v2 client,
which required the entire assistant message to be a JSON string. Thus no
recipe normalization, renderer expansion, verifier gate, or candidate
admission was reached. The three requests remain in the append-only ledger and
count toward the unchanged 100-request ceiling.

## Narrow correction

The S-C client now extracts the first syntactically valid JSON object from the
assistant-message content, including content wrapped in prose or a Markdown
code fence. It still passes that object through the unchanged exact-key recipe
schema and fixed numeric bounds before rendering. A response with no JSON
object, an invalid object, or a schema violation remains a counted rejection.

No prompt statistic, renderer, direction, certificate, admission boundary,
feedback limit, downstream protocol, secret handling, or formal-data boundary
changes. This is a transport decoder correction, not a threshold relaxation.

Exactly three additional smoke requests are permitted, giving six cumulative
S-C attempts. They revisit the one pending slot per class. Full generation
remains prohibited unless the amended smoke admits one sample per class.
