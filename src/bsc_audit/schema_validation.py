from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from .findings import Finding, Severity


ROUTE_SCHEMAS = {
    "lint": "claim-manifest-v0.3.schema.json",
    "audit": "claim-manifest-v0.3.schema.json",
    "complex": "complex-v0.3.schema.json",
    "observe": "observation-v0.3.schema.json",
    "atomic": "atomic-modulus-v0.3.schema.json",
    "defect": "defect-v0.3.schema.json",
    "adapter": "adapter-receipt-v0.1.schema.json",
    "holonomy": "derived-holonomy-v0.1.schema.json",
}


@dataclass(frozen=True)
class SchemaViolation:
    path: str
    message: str


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"only local schema references are supported: {reference}")
    value: Any = root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    if not isinstance(value, dict):
        raise ValueError(f"schema reference does not resolve to an object: {reference}")
    return value


def _validate(value: Any, schema: Any, root: dict[str, Any], path: str) -> list[SchemaViolation]:
    if schema is True or schema == {}:
        return []
    if schema is False:
        return [SchemaViolation(path, "value is forbidden by the schema")]
    if not isinstance(schema, dict):
        return [SchemaViolation(path, "invalid internal schema node")]
    if "$ref" in schema:
        return _validate(value, _resolve_ref(root, schema["$ref"]), root, path)

    violations: list[SchemaViolation] = []
    if "allOf" in schema:
        for member in schema["allOf"]:
            violations.extend(_validate(value, member, root, path))
    if "oneOf" in schema:
        matches = sum(not _validate(value, member, root, path) for member in schema["oneOf"])
        if matches != 1:
            violations.append(SchemaViolation(path, "value must satisfy exactly one allowed schema"))
            return violations
    if "if" in schema and not _validate(value, schema["if"], root, path):
        violations.extend(_validate(value, schema.get("then", {}), root, path))

    expected = schema.get("type")
    if expected is not None:
        alternatives = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(value, item) for item in alternatives):
            violations.append(SchemaViolation(path, f"expected type {alternatives}, found {type(value).__name__}"))
            return violations
    if "const" in schema and value != schema["const"]:
        violations.append(SchemaViolation(path, f"expected constant value {schema['const']!r}"))
    if "enum" in schema and value not in schema["enum"]:
        violations.append(SchemaViolation(path, f"value is not one of {schema['enum']!r}"))

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            violations.append(SchemaViolation(path, f"string is shorter than {schema['minLength']} characters"))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            violations.append(SchemaViolation(path, f"string is longer than {schema['maxLength']} characters"))
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            violations.append(SchemaViolation(path, "string does not match the required pattern"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            violations.append(SchemaViolation(path, f"number is below minimum {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            violations.append(SchemaViolation(path, f"number exceeds maximum {schema['maximum']}"))

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            violations.append(SchemaViolation(path, f"array has fewer than {schema['minItems']} items"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            violations.append(SchemaViolation(path, f"array has more than {schema['maxItems']} items"))
        if schema.get("uniqueItems"):
            keys = [_json_key(item) for item in value]
            if len(keys) != len(set(keys)):
                violations.append(SchemaViolation(path, "array items must be unique"))
        prefix = schema.get("prefixItems", [])
        for index, member in enumerate(prefix):
            if index < len(value):
                violations.extend(_validate(value[index], member, root, f"{path}.{index}"))
        if "items" in schema:
            item_schema = schema["items"]
            for index in range(len(prefix), len(value)):
                violations.extend(_validate(value[index], item_schema, root, f"{path}.{index}"))

    if isinstance(value, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                violations.append(SchemaViolation(f"{path}.{name}", "required property is missing"))
        if len(value) < schema.get("minProperties", 0):
            violations.append(SchemaViolation(path, f"object has fewer than {schema['minProperties']} properties"))
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            violations.append(SchemaViolation(path, f"object has more than {schema['maxProperties']} properties"))
        property_names = schema.get("propertyNames")
        if property_names:
            for name in value:
                violations.extend(_validate(name, property_names, root, f"{path}.{name}"))
        properties = schema.get("properties", {})
        for name, nested in value.items():
            nested_path = f"{path}.{name}"
            if name in properties:
                violations.extend(_validate(nested, properties[name], root, nested_path))
            elif "additionalProperties" in schema:
                violations.extend(_validate(nested, schema["additionalProperties"], root, nested_path))
        for trigger, dependencies in schema.get("dependentRequired", {}).items():
            if trigger in value:
                for dependency in dependencies:
                    if dependency not in value:
                        violations.append(SchemaViolation(f"{path}.{dependency}", f"property is required when {trigger!r} is present"))
    return violations


def load_schema(route: str) -> dict[str, Any]:
    name = ROUTE_SCHEMAS[route]
    resource = files("bsc_audit").joinpath("schema_data", name)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_route_schema(route: str, value: dict[str, Any]) -> list[Finding]:
    if route not in ROUTE_SCHEMAS:
        return []
    schema = load_schema(route)
    violations = _validate(value, schema, schema, "$")
    return [
        Finding(Severity.ERROR, "SCHEMA_VALIDATION", violation.path, violation.message)
        for violation in violations[:100]
    ]
