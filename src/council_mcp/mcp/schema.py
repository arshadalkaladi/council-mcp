"""Minimal closed-schema validation/coercion for tool inputs.

Supports the small JSON-Schema subset our tools use:
  {"type": "object",
   "properties": {"field": {"type": "string|integer|number|boolean|array|object"}},
   "required": [...],
   "additionalProperties": false}

Unknown keys are dropped (closed schema). Type mismatches and missing required
fields are reported as errors. This is deliberately tiny and dependency-free; a
richer validator can replace it behind the same signature later.
"""

from __future__ import annotations

_PY_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _type_ok(json_type: str, value) -> bool:
    # bool is a subclass of int; keep them distinct.
    if json_type in ("integer", "number") and isinstance(value, bool):
        return False
    if json_type == "boolean":
        return isinstance(value, bool)
    py = _PY_TYPES.get(json_type)
    if py is None:
        return True  # unknown type constraint => don't reject
    return isinstance(value, py)


def validate_and_coerce(schema: dict, data) -> tuple[dict, list[str]]:
    """Return (cleaned_data, errors). cleaned_data drops unknown keys."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return {}, ["arguments must be an object"]

    props = schema.get("properties", {})
    cleaned: dict = {}
    for key, value in data.items():
        if key in props:
            cleaned[key] = value
        # else: unknown key dropped (additionalProperties: false)

    for name, spec in props.items():
        if name in cleaned:
            jtype = spec.get("type")
            if jtype is not None and not _type_ok(jtype, cleaned[name]):
                errors.append(f"field '{name}' must be of type {jtype}")

    for req in schema.get("required", []):
        if req not in cleaned:
            errors.append(f"missing required field: {req}")

    return cleaned, errors
