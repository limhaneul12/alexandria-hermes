# Boundary and Normalization Rules

## Goal

Keep raw OMX payloads from spreading unchecked through the adapter.

## Boundary Categories

### 1. Agent input boundary
These are requests entering the adapter from callers.

### 2. OMX output boundary
These are payloads coming from OMX, including JSON, JSONL event lines, and normalized command outputs.

### 3. Adapter public output boundary
These are structured results returned to callers.

### 4. Settings/config boundary
These are validated settings inputs when configuration needs a schema.

## Early Normalization Rule

Raw OMX output should be converted into stable adapter contracts early, but not prematurely.

Preferred flow:
1. receive raw OMX output
2. parse the transport unit minimally
3. route or normalize based on event/source shape
4. validate the canonical contract boundary with Pydantic
5. convert to an inner dataclass or `TypedDict` DTO when domain/application
   logic should own the value
6. pass structured values onward

Do not keep raw dictionaries moving through multiple layers when a stable schema can be defined.
Do not force every inbound payload into a canonical schema before transport parsing and routing are complete.
Do not keep Pydantic request/response schemas as the default internal DTO after
the I/O boundary has been crossed.

## Schema Placement Rule

Keep Pydantic I/O schemas under the nearest existing schema boundary for the
current slice.

In this backend that often means `interface/schemas/...`; in a smaller slice it
may mean a local `schemas/` folder. Follow the current path shape instead of
creating a hard-coded example path.

Split schemas by concept using:
- `{concept}_schemas.py`

Examples:
- `execution_schemas.py`
- `runtime_schemas.py`
- `teamwork_schemas.py`
- `history_schemas.py`
- `bridge_schemas.py`

These examples are naming patterns, not mandatory directory roots.

## Dynamic Boundary Rule

Some OMX surfaces may remain dynamic in practice.

When that happens:
- keep the dynamic handling localized,
- add a short justification comment if necessary,
- allow a raw passthrough lane when transport parsing succeeded but canonical schema promotion is not yet justified,
- convert to an explicit schema as soon as the stable structure is understood,
- do not let dynamic looseness leak into the stable adapter API.

## Enum Normalization Rule

Do not add `mode="before"` validators solely to convert public enum strings
into enum members.

Pydantic already validates string-backed enum fields, including optional enum
fields, against the annotated enum contract. A before validator is justified
only when it adds real boundary behavior such as legacy aliases, non-standard
external payload shapes, or null/default normalization that Pydantic would not
perform from the field annotation alone.

When a before validator is justified for one small normalization rule, normalize
only that rule and return the value for Pydantic to validate against the
annotated field. Do not duplicate the full enum/type validation path inside the
validator.

Bad direction:

```python
@field_validator("status", mode="before")
@classmethod
def parse_status(cls, value: object) -> ItemStatus:
    if isinstance(value, ItemStatus):
        return value
    if isinstance(value, str):
        return ItemStatus(value)
    raise ValueError("status must be a valid item status")
```

Preferred direction:

```python
status: ItemStatus = ItemStatus.DRAFT
```

This keeps strict typing focused on real contracts instead of framework
reimplementation.
