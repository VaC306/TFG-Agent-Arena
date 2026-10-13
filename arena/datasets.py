"""Portable user datasets. Parsing never accesses paths supplied by a dataset."""
import csv
import io
from pydantic import Field, ValidationError, model_validator
from .contracts import Contract, Task
from .json_input import load_json


class DatasetCase(Contract):
    id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')
    input: str = Field(min_length=1, max_length=6000)
    expected_answer: str | None = Field(default=None, min_length=1, max_length=6000)

    @model_validator(mode='after')
    def nonblank(self):
        if not self.input.strip() or (self.expected_answer is not None and not self.expected_answer.strip()):
            raise ValueError('La entrada y la referencia, si existe, no pueden estar en blanco')
        return self

    def task(self):
        return Task(**self.model_dump(), split='dev', environment='empty')


def validate_cases(cases):
    if not 1 <= len(cases) <= 100:
        raise ValueError('El dataset debe contener entre 1 y 100 casos')
    if len({case.id for case in cases}) != len(cases):
        raise ValueError('Cada caso debe tener un id único')
    return cases


def parse_dataset(filename: str, content: str):
    if len(content.encode('utf-8')) > 1024 * 1024:
        raise ValueError('El dataset supera 1 MiB')
    content = content.removeprefix('\ufeff')
    rows = []
    if filename.lower().endswith('.csv'):
        reader = csv.DictReader(io.StringIO(content, newline=''), strict=True)
        try:
            headers = reader.fieldnames or []
        except csv.Error as exc:
            raise ValueError('Cabecera CSV inválida') from exc
        if (not {'id', 'input'} <= set(headers) or len(set(headers)) != len(headers)
                or set(headers) - {'id', 'input', 'expected_answer'}):
            raise ValueError('Cabecera CSV: id,input,expected_answer (la última columna es opcional)')
        try:
            for row in reader:
                rows.append((reader.line_num, row))
                if len(rows) > 100:
                    raise ValueError('Máximo 100 casos por dataset')
        except csv.Error as exc:
            raise ValueError(f'CSV incorrecto en línea {reader.line_num}: {exc}') from exc
    elif filename.lower().endswith('.jsonl'):
        for number, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = load_json(line)
            except ValueError as exc:
                raise ValueError(f'Línea {number}: JSON inválido') from exc
            rows.append((number, row))
            if len(rows) > 100:
                raise ValueError('Máximo 100 casos por dataset')
    else:
        raise ValueError('Selecciona un archivo .csv o .jsonl en UTF-8')
    cases = []
    seen = {}
    for number, row in rows:
        if not isinstance(row, dict) or None in row or any(value is None for key, value in row.items() if key != 'expected_answer'):
            raise ValueError(f'Línea {number}: se esperaba un caso con columnas completas')
        if row.get('expected_answer') == '':
            row['expected_answer'] = None
        try:
            case = DatasetCase.model_validate(row)
        except ValidationError as exc:
            error = exc.errors(include_input=False)[0]
            raise ValueError(f'Línea {number}, {" / ".join(map(str, error["loc"]))}: {error["msg"]}') from exc
        if case.id in seen:
            raise ValueError(f'ID duplicado «{case.id}»: filas {seen[case.id]} y {number} (líneas del archivo)')
        seen[case.id] = number
        cases.append(case)
    return validate_cases(cases)


class DatasetUpload(Contract):
    filename: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=1024 * 1024)

    @model_validator(mode='after')
    def safe_filename(self):
        if '/' in self.filename or '\\' in self.filename or any(ord(c) < 32 or ord(c) == 127 for c in self.filename):
            raise ValueError('El nombre del dataset no puede contener rutas ni caracteres de control')
        return self
