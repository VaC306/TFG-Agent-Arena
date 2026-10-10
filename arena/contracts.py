from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator('*')
    @classmethod
    def safe_text(cls, value):
        if isinstance(value, str):
            if '\x00' in value:
                raise ValueError('El texto no puede contener caracteres nulos')
            try:
                value.encode('utf-8')
            except UnicodeEncodeError as exc:
                raise ValueError('El texto debe contener Unicode válido') from exc
        return value


class Limits(Contract):
    timeout_s: float = Field(default=120, gt=0, le=3600)
    max_calls: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=30, ge=0, le=300)
    max_output_tokens: int = Field(default=4096, ge=1, le=65536)


class AgentConfig(Contract):
    model: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    temperature: float = Field(default=0, ge=0, le=2)
    seed: int | None = 42
    num_ctx: int = Field(default=8192, ge=512)
    limits: Limits = Field(default_factory=Limits)
    prompt_template: str = "custom"
    tools_enabled: bool = True


class Attachment(Contract):
    name: str
    media_type: str
    size: int
    sha256: str
    data_base64: str
    text: str | None = None


class Criteria(Contract):
    total_cents: int = Field(ge=0)
    order_ids: list[str]
    allowed_tools: list[str] = ["search_orders", "order_lines", "calculate"]


class Task(Contract):
    id: str
    split: Literal["dev", "eval"]
    input: str
    environment: str
    criteria: Criteria | None = None
    expected_answer: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)


class Experiment(Contract):
    name: str
    adapter: Literal["simulated", "ollama"] = "simulated"
    mode: Literal["sequential"] = "sequential"
    agents: dict[str, AgentConfig]
    split: Literal["dev", "eval"] = "dev"
    repetitions: int = Field(default=1, ge=1, le=100)
    order_seed: int = 42
    ollama_url: str = "http://127.0.0.1:11434"
    comparison: Literal["same_model", "different_models"] = "same_model"

    @model_validator(mode="after")
    def paired_model(self):
        if set(self.agents) != {"A", "B"}:
            raise ValueError("Se requieren exactamente las ramas A y B")
        models = [a.model if ':' in a.model else a.model + ':latest' for a in self.agents.values()]
        if self.comparison == "same_model" and models[0] != models[1]:
            raise ValueError("El modo un modelo exige el mismo modelo en A y B")
        if self.comparison == "different_models" and models[0] == models[1]:
            raise ValueError("Selecciona dos modelos distintos")
        return self


Status = Literal["queued", "running", "completed", "succeeded", "failed", "timeout", "limit", "cancelled", "interrupted"]


class Run(Contract):
    id: str
    experiment_id: str
    task_id: str
    branch: Literal["A", "B"]
    repetition: int
    position: int
    status: Status = "queued"
    queued_at: float
    started_at: float | None = None
    finished_at: float | None = None
    result: dict | None = None


class Event(Contract):
    run_id: str
    kind: str
    at: float
    payload: dict


class ResourceSample(Contract):
    at: float
    scope: Literal["host_and_worker"] = "host_and_worker"
    ram_available_bytes: int | None = None
    worker_rss_bytes: int | None = None
    gpu: list[dict] | None = None
    unavailable: list[str] = []
