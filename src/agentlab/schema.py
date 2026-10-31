"""A small JSON Schema validator covering the keywords tool and output schemas use most."""

from typing import Any

_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}


def validate(instance: object, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Check ``instance`` against a JSON Schema.

    Supports ``type`` (a name or a list of names), ``enum``, ``const``, ``properties``, ``required``,
    ``additionalProperties`` (boolean), ``items``, ``minItems``, ``maxItems``, ``minLength``,
    ``maxLength``, ``minimum`` and ``maximum``. Other keywords are ignored.

    Args:
        instance: The parsed JSON value.
        schema: The schema.
        path: Location of ``instance`` used in messages; ``$`` is the root.

    Returns:
        One message per problem, such as ``"$.city: expected string, got int"``; empty when valid.
    """
    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(instance, name) for name in names):
            return [f"{path}: expected {' or '.join(names)}, got {_type_name(instance)}"]
    problems: list[str] = []
    if "enum" in schema and instance not in schema["enum"]:
        problems.append(f"{path}: {instance!r} is not one of {schema['enum']!r}")
    if "const" in schema and instance != schema["const"]:
        problems.append(f"{path}: expected {schema['const']!r}")
    if isinstance(instance, dict):
        problems.extend(_validate_object(instance, schema, path))
    elif isinstance(instance, list):
        problems.extend(_validate_array(instance, schema, path))
    elif isinstance(instance, str):
        problems.extend(_bounds(len(instance), schema, "minLength", "maxLength", path, "length"))
    elif isinstance(instance, int | float) and not isinstance(instance, bool):
        problems.extend(_bounds(instance, schema, "minimum", "maximum", path, "value"))
    return problems


def _validate_object(instance: dict[str, Any], schema: dict[str, Any], path: str) -> list[str]:
    problems = [
        f"{path}: missing required property {key!r}" for key in schema.get("required", []) if key not in instance
    ]
    properties: dict[str, Any] = schema.get("properties", {})
    for key, value in instance.items():
        if key in properties:
            problems.extend(validate(value, properties[key], f"{path}.{key}"))
        elif schema.get("additionalProperties") is False:
            problems.append(f"{path}: unexpected property {key!r}")
    return problems


def _validate_array(instance: list[Any], schema: dict[str, Any], path: str) -> list[str]:
    problems = _bounds(len(instance), schema, "minItems", "maxItems", path, "item count")
    items = schema.get("items")
    if isinstance(items, dict):
        for index, value in enumerate(instance):
            problems.extend(validate(value, items, f"{path}[{index}]"))
    return problems


def _bounds(value: float, schema: dict[str, Any], low: str, high: str, path: str, label: str) -> list[str]:
    problems: list[str] = []
    if low in schema and value < schema[low]:
        problems.append(f"{path}: {label} {value} is below {low} {schema[low]}")
    if high in schema and value > schema[high]:
        problems.append(f"{path}: {label} {value} is above {high} {schema[high]}")
    return problems


def _is_type(instance: object, name: str) -> bool:
    if name in {"integer", "number"} and isinstance(instance, bool):
        return False
    if name == "integer" and isinstance(instance, float):
        return instance.is_integer()
    return isinstance(instance, _TYPES.get(name, ()))


def _type_name(instance: object) -> str:
    return "null" if instance is None else type(instance).__name__
