import json
import re
import httpx
from .tools import SCHEMAS


class Ollama:
    def __init__(self, url, keep_alive='5m'):
        self.url = url.rstrip("/")
        self.keep_alive = keep_alive

    async def models(self):
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.get(self.url + '/api/tags')
            response.raise_for_status()
        return response.json()['models']

    async def metadata(self, model):
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            version = await client.get(self.url + "/api/version")
            version.raise_for_status()
            show = await client.post(self.url + "/api/show", json={"model": model})
            show.raise_for_status()
            tags = await client.get(self.url + "/api/tags")
            tags.raise_for_status()
        matching = [m for m in tags.json()["models"] if m["name"] in {model, model + ":latest"}]
        if not matching:
            raise ValueError("El modelo debe estar instalado localmente y aparecer en /api/tags")
        return {"version": version.json(), "show": show.json(), "model": matching[0]}

    def payload(self, messages, config, remaining):
        options = {"temperature": config.temperature, "num_predict": remaining, "num_ctx": config.num_ctx}
        if config.seed is not None:
            options["seed"] = config.seed
        payload = {"model": config.model, "messages": messages,
                   "stream": False, "options": options, "keep_alive": self.keep_alive}
        if config.tools_enabled:
            payload['tools'] = SCHEMAS
        return payload

    async def chat(self, messages, config, remaining):
        async with httpx.AsyncClient(timeout=None, trust_env=False) as client:
            payload = self.payload(messages, config, remaining)
            response = await client.post(self.url + "/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        # Never require or persist the model's private thinking field.
        data["message"].pop("thinking", None)
        return data


class Simulated:
    """Deterministic fixture agent; derives answers only from input and tool results."""
    async def metadata(self, model):
        return {"adapter": "simulated-v1", "model": model, "quantization": None,
                "warning": "Synthetic token counts and durations; not model quality evidence"}

    async def chat(self, messages, config, remaining):
        user = next(m["content"] for m in messages if m["role"] == "user")
        if not config.tools_enabled:
            images = sum(len(m.get('images', [])) for m in messages)
            return {'message': {'role': 'assistant', 'content':
                f'SIMULACIÓN — modelo {config.model}. Entrada recibida:\n{user[:1800]}\n'
                f'Imágenes recibidas: {images}. El simulador no interpreta imágenes ni mide calidad del modelo.'},
                'done': True, 'done_reason': 'stop', 'prompt_eval_count': 10 * len(messages),
                'eval_count': min(8, remaining), 'eval_duration': 8_000_000, 'simulated': True}
        customer = re.search(r"cliente=(\w+)", user).group(1)
        month = re.search(r"mes=(\d{4}-\d{2})", user).group(1)
        outputs = [m for m in messages if m["role"] == "tool"]

        def call(name, args):
            return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}

        if not outputs:
            message = call("search_orders", {"customer_id": customer})
        else:
            orders = json.loads(outputs[0]["content"])
            ids = [o["id"] for o in orders if o["status"] == "delivered" and o["date"].startswith(month)]
            if "inverso" in config.system_prompt:
                ids.reverse()
            lines = [json.loads(m["content"]) for m in outputs if m["tool_name"] == "order_lines"]
            if len(lines) < len(ids):
                message = call("order_lines", {"order_id": ids[len(lines)]})
            elif outputs[-1]["tool_name"] != "calculate":
                amounts = [l["unit_cents"] * (l["quantity"] - l["returned_quantity"]) for group in lines for l in group]
                message = call("calculate", {"operation": "sum", "values": amounts or [0]})
            else:
                included = [oid for oid, group in zip(ids, lines) if any(l["quantity"] > l["returned_quantity"] for l in group)]
                message = {"role": "assistant", "content": json.dumps({"total_cents": json.loads(outputs[-1]["content"])["value"], "order_ids": included})}
        return {"message": message, "done": True, "done_reason": "stop",
                "prompt_eval_count": 10 * len(messages), "eval_count": min(8, remaining),
                "eval_duration": 8_000_000, "simulated": True}
