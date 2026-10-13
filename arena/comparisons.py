from typing import Literal
from pydantic import Field, model_validator, field_validator
from .attachments import AttachmentUpload, prepare_attachment, MAX_TEXT_CHARS
from .contracts import Contract, AgentConfig, Experiment, Task
from .scheduler import schedule
from .datasets import DatasetCase, validate_cases

PROMPTS = [
    {'id': 'general', 'name': 'Asistente general', 'text': 'Responde a la solicitud usando el contenido proporcionado. Distingue hechos de suposiciones y señala la información que falta.'},
    {'id': 'analyst', 'name': 'Análisis de datos', 'text': 'Analiza los datos proporcionados. Identifica patrones, inconsistencias y limitaciones. Explica los resultados con claridad y no inventes cifras.'},
    {'id': 'summary', 'name': 'Resumen', 'text': 'Resume el contenido proporcionado de forma concisa. Conserva los hechos, cifras y conclusiones relevantes. Indica si no puedes interpretar algún contenido.'},
    {'id': 'extract', 'name': 'Extracción JSON', 'text': 'Extrae la información solicitada y devuelve únicamente JSON válido. Usa null para valores que no estén disponibles. No inventes información.'},
    {'id': 'vision', 'name': 'Descripción de imágenes', 'text': 'Describe lo que se observa en las imágenes y responde a la solicitud. Distingue lo visible de lo inferido y no inventes detalles ilegibles.'},
    {'id': 'custom', 'name': 'Personalizado', 'text': ''},
]


class InputBundle(Contract):
    text: str = Field(min_length=1, max_length=6000)
    files: list[AttachmentUpload] = Field(default_factory=list, max_length=4)
    expected_answer: str | None = Field(default=None, min_length=1, max_length=6000)

    @field_validator('text')
    @classmethod
    def nonblank_input(cls, value):
        if not value.strip():
            raise ValueError('Escribe una entrada para el agente')
        return value

    @field_validator('expected_answer', mode='before')
    @classmethod
    def empty_reference(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    def task(self):
        attachments = [prepare_attachment(file) for file in self.files]
        if not self.text.strip():
            raise ValueError('Escribe una entrada para el agente')
        if len({file.name for file in attachments}) != len(attachments):
            raise ValueError('No se admiten nombres de archivo duplicados en la misma entrada')
        if sum(len(file.text or '') for file in attachments) > MAX_TEXT_CHARS:
            raise ValueError('El texto de los adjuntos no puede superar 20.000 caracteres por entrada')
        return Task(id='custom-input', split='dev', input=self.text, environment='empty',
                    expected_answer=self.expected_answer, attachments=attachments)


class CustomAgent(Contract):
    model: str = Field(min_length=1, max_length=120, pattern=r'^[A-Za-z0-9][A-Za-z0-9._:/-]*$')
    system_prompt: str = Field(min_length=1, max_length=6000)
    prompt_template: Literal['general', 'analyst', 'summary', 'extract', 'vision', 'custom'] = 'custom'


class InferenceSettings(Contract):
    temperature: float = Field(default=0, ge=0, le=2, allow_inf_nan=False, strict=True)
    seed: int = Field(default=42, ge=0, le=2_147_483_647, strict=True)
    num_ctx: int = Field(default=16384, ge=512, le=131072, strict=True)
    max_output_tokens: int = Field(default=4096, ge=1, le=16384, strict=True)
    timeout_s: int = Field(default=120, ge=1, le=3600, strict=True)
    warmup: Literal['none','per_run'] = 'none'
    order_policy: Literal['random','balanced'] = 'random'
    latency_study: bool = Field(default=False,strict=True)
    planned_attempts: int = Field(default=2,ge=2,le=20,strict=True)

    @model_validator(mode='after')
    def context_budget(self):
        if self.max_output_tokens >= self.num_ctx:
            raise ValueError('El máximo de salida debe ser menor que el contexto para dejar espacio a la entrada')
        return self


class ComparisonRequest(Contract):
    name: str = Field(min_length=1, max_length=120)
    adapter: Literal['simulated', 'ollama']
    comparison: Literal['same_model', 'different_models']
    agents: dict[str, CustomAgent]
    shared_input: InputBundle | None = None
    branch_inputs: dict[str, InputBundle] | None = None
    repetitions: int = Field(default=1, ge=1, le=10, strict=True)
    dataset: list[DatasetCase] | None = Field(default=None, min_length=1, max_length=100)
    evaluation: Literal['exact_match', 'json_match', 'none'] = 'exact_match'
    settings: InferenceSettings = Field(default_factory=InferenceSettings)
    split: Literal['dev', 'eval'] = 'dev'

    @field_validator('name')
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError('Escribe un nombre para la comparación')
        return value.strip()

    @model_validator(mode='after')
    def validate_design(self):
        if self.settings.latency_study and (self.dataset is None or self.evaluation == 'none' or any(c.expected_answer is None for c in self.dataset)):
            raise ValueError('El estudio de latencia requiere un dataset compartido con referencia evaluable en todos los casos.')
        if set(self.agents) != {'A', 'B'}:
            raise ValueError('Se necesitan exactamente las ramas A y B')
        if any(not agent.system_prompt.strip() for agent in self.agents.values()):
            raise ValueError('El prompt no puede estar vacío')
        references = ([case.expected_answer for case in self.dataset] if self.dataset is not None else
                      [self.shared_input.expected_answer] if self.shared_input else
                      [bundle.expected_answer for bundle in (self.branch_inputs or {}).values()])
        if self.evaluation == 'json_match':
            from .json_input import load_json
            for reference in references:
                if reference is not None:
                    try:
                        load_json(reference)
                    except ValueError as exc:
                        raise ValueError('La evaluación JSON requiere respuestas esperadas con JSON válido') from exc
        self.config()  # Enforce model identity on the server, not just in the form.
        if self.dataset is not None:
            validate_cases(self.dataset)
            if self.shared_input is not None or self.branch_inputs is not None:
                raise ValueError('Elige dataset o entradas manuales, no ambos')
            return self
        if self.comparison == 'different_models':
            if self.shared_input is None or self.branch_inputs is not None:
                raise ValueError('Dos modelos requieren una única entrada y archivos compartidos')
        elif self.shared_input is not None:
            if self.branch_inputs is not None:
                raise ValueError('Elige entrada compartida o entradas independientes, no ambas')
        elif self.branch_inputs is None or set(self.branch_inputs) != {'A', 'B'}:
            raise ValueError('Un modelo requiere una entrada compartida o entradas A y B completas')
        return self

    def config(self):
        return Experiment(name=self.name, adapter=self.adapter, comparison=self.comparison,
                          warmup=self.settings.warmup,
                          order_policy=self.settings.order_policy,latency_study=self.settings.latency_study,
                          planned_attempts=self.settings.planned_attempts,
                          repetitions=self.repetitions, split=self.split, agents={branch: AgentConfig(
                              **agent.model_dump(), tools_enabled=False, temperature=self.settings.temperature,
                              seed=self.settings.seed, num_ctx=self.settings.num_ctx,
                              limits={'max_output_tokens':self.settings.max_output_tokens, 'timeout_s':self.settings.timeout_s},
                          ) for branch, agent in self.agents.items()})


def submit_comparison(store, request):
    config = request.config()
    if request.dataset is not None:
        tasks = [case.task().model_copy(update={'evaluation':request.evaluation, 'split':request.split}) for case in request.dataset]
        return schedule(store, config, tasks, {'empty': {'orders': []}})
    if request.shared_input:
        tasks = [request.shared_input.task().model_copy(update={'evaluation':request.evaluation, 'split':request.split})]
        branch_tasks = None
    else:
        branch_tasks = {branch: bundle.task().model_copy(update={'evaluation':request.evaluation, 'split':request.split}).model_dump() for branch, bundle in request.branch_inputs.items()}
        tasks = [Task.model_validate(branch_tasks['A'])]
    return schedule(store, config, tasks, {'empty': {'orders': []}}, branch_tasks)
