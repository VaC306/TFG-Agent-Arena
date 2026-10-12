from pydantic import StrictInt, StrictStr
from .contracts import Contract, Task
from .json_input import load_json

EVALUATOR_VERSION = 'arena-evaluation-v2'


def json_equal(a, b):
    # Python would consider True == 1. JSON booleans must remain distinct from numbers.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(json_equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b or type(a) in (int, float) and type(b) in (int, float) and a == b


class Answer(Contract):
    total_cents: StrictInt
    order_ids: list[StrictStr]


def evaluate(content: str, task: Task, tool_names: list[str]) -> dict:
    if task.criteria is None:
        if task.evaluation == 'none' or task.expected_answer is None:
            return {'success': None, 'format_ok': None, 'evaluation': 'not_evaluated', 'reason': 'Calidad no evaluada automáticamente'}
        if task.evaluation == 'json_match':
            try:
                answer = load_json(content)
                reference = load_json(task.expected_answer)
                correct = json_equal(answer, reference)
            except (ValueError, RecursionError):
                return {'success':False, 'format_ok':False, 'evaluation':'json_match', 'reason':'Respuesta JSON inválida'}
            return {'success':correct, 'format_ok':True, 'evaluation':'json_match',
                    'reason':'JSON equivalente a la referencia' if correct else 'El JSON contiene valores o estructura distintos'}
        return {'success': content.strip() == task.expected_answer.strip(), 'format_ok': None,
                'evaluation': 'exact_match', 'reason': 'Comparación exacta con la respuesta esperada (sin espacios en los extremos)'}
    try:
        answer = Answer.model_validate(load_json(content))
    except (ValueError, TypeError):
        return {"success": False, "format_ok": False, "evaluation":"order_benchmark", "reason": "Respuesta JSON inválida"}
    unique = len(answer.order_ids) == len(set(answer.order_ids))
    correct = answer.total_cents == task.criteria.total_cents and set(answer.order_ids) == set(task.criteria.order_ids)
    allowed = set(tool_names).issubset(task.criteria.allowed_tools)
    return {"success": bool(unique and correct and allowed), "format_ok": True, "evaluation":"order_benchmark",
            "reason": "ok" if unique and correct and allowed else "Importe, identificadores o restricciones incorrectos"}
