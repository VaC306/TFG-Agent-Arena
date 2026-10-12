"""Strict JSON ingestion with safe messages for user-supplied content."""
import json
import math


def load_json(value):
    def unique_object(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError('El JSON contiene campos duplicados')
            result[key] = item
        return result

    def invalid_number(_):
        raise ValueError('El JSON contiene un número no válido')

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            invalid_number(value)
        return result

    try:
        return json.loads(value, object_pairs_hook=unique_object, parse_constant=invalid_number, parse_float=finite_float)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise ValueError('JSON inválido o demasiado anidado') from exc
