"""Strict JSON ingestion with safe messages for user-supplied content."""
import json


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

    try:
        return json.loads(value, object_pairs_hook=unique_object, parse_constant=invalid_number)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise ValueError('JSON inválido o demasiado anidado') from exc
