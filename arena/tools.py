import copy
from typing import Literal
from pydantic import Field, StrictInt
from .contracts import Contract


class SearchArgs(Contract):
    customer_id: str


class LinesArgs(Contract):
    order_id: str


class CalculateArgs(Contract):
    operation: Literal["sum", "multiply", "subtract"]
    values: list[StrictInt] = Field(min_length=1, max_length=1000)


ARGUMENTS = {"search_orders": SearchArgs, "order_lines": LinesArgs, "calculate": CalculateArgs}
DESCRIPTIONS = {
    "search_orders": "Busca pedidos por customer_id; devuelve id, fecha y estado, sin líneas.",
    "order_lines": "Obtiene productos, cantidades, cantidades devueltas y precios en céntimos de un pedido.",
    "calculate": "Aritmética entera en céntimos: sum suma; multiply multiplica; subtract resta del primer valor los restantes.",
}
SCHEMAS = [{"type": "function", "function": {"name": name, "description": DESCRIPTIONS[name],
            "parameters": cls.model_json_schema()}} for name, cls in ARGUMENTS.items()]


class Tools:
    def __init__(self, environment):
        self.environment = copy.deepcopy(environment)

    def call(self, name, arguments):
        if name not in ARGUMENTS:
            raise ValueError(f"Herramienta no permitida: {name}")
        args = ARGUMENTS[name].model_validate(arguments)
        orders = self.environment["orders"]
        if name == "search_orders":
            return [{k: v for k, v in o.items() if k != "lines"} for o in orders if o["customer_id"] == args.customer_id]
        if name == "order_lines":
            for order in orders:
                if order["id"] == args.order_id:
                    return copy.deepcopy(order["lines"])
            raise ValueError("Pedido inexistente")
        values = args.values
        if any(abs(v) > 10**12 for v in values):
            raise ValueError("Importe fuera de rango")
        if args.operation == "sum":
            result = sum(values)
        elif args.operation == "subtract":
            result = values[0] - sum(values[1:])
        else:
            result = 1
            for value in values:
                result *= value
                if abs(result) > 10**15:
                    raise ValueError("Resultado fuera de rango")
        return {"value": result}
