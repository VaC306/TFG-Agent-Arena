import json
from pydantic import StrictInt, StrictStr
from .contracts import Contract, Task


class Answer(Contract):
    total_cents: StrictInt
    order_ids: list[StrictStr]


def evaluate(content: str, task: Task, tool_names: list[str]) -> dict:
    try:
        answer = Answer.model_validate(json.loads(content))
    except (ValueError, TypeError):
        return {"success": False, "format_ok": False, "reason": "Respuesta JSON inválida"}
    unique = len(answer.order_ids) == len(set(answer.order_ids))
    correct = answer.total_cents == task.criteria.total_cents and set(answer.order_ids) == set(task.criteria.order_ids)
    allowed = set(tool_names).issubset(task.criteria.allowed_tools)
    return {"success": bool(unique and correct and allowed), "format_ok": True,
            "reason": "ok" if unique and correct and allowed else "Importe, identificadores o restricciones incorrectos"}
