# Enums, Literals, and Shared Types Rules

## Enum Rule

Keep enums with enums.

Place enums in the nearest concept-owned enum path for the current slice.

Shared cross-cutting enum definitions may belong under:

```text
shared/
└── omx_enums/
    ├── runtime_enums.py
    ├── execution_enums.py
    ├── teamwork_enums.py
    ├── history_enums.py
    └── bridge_enums.py
```

Split enum files by concept.
Do not create a giant `enums.py` catch-all.
Do not force this example path when the current slice already has a clearer
enum location such as `domain/event_enum/{concept}_enums.py`.

## Literal and Enum Usage Rule

For narrow protocol value sets, prefer explicit constrained representations over loose strings.

Good candidates:
- event kinds
- runtime modes
- bridge target kinds
- small protocol-local constants

### Project stance

- Use `Literal` when the value set is small and local to one contract.
- Use enums when the symbolic value set is shared across multiple contracts or modules.

## Shared Types Rule

If shared type aliases or reusable typed helpers remain small, a local `types.py` may be temporarily acceptable in a tightly scoped directory.

If that surface grows, split it into a `types/` directory and use concept-based files such as:
- `runtime_types.py`
- `execution_types.py`
- `teamwork_types.py`
- `bridge_types.py`

The larger the project becomes, the less acceptable one generic `types.py` file becomes.
