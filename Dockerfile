FROM python:3.11.9-slim
WORKDIR /app
COPY requirements.lock requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml README.md ./
COPY arena arena
COPY configs configs
COPY data data
RUN pip install --no-deps --no-build-isolation .
CMD ["python", "-m", "arena.cli", "worker"]
