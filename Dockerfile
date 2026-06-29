FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MNEMOSYNE_SERVICE_HOST=0.0.0.0
ENV MNEMOSYNE_SERVICE_PORT=8088

COPY pyproject.toml README.md ./
COPY mnemosyne ./mnemosyne
COPY benchmarks ./benchmarks
COPY examples ./examples
COPY experiments ./experiments

RUN pip install --no-cache-dir -e .

EXPOSE 8088

CMD ["python", "-m", "mnemosyne.service.app", "--host", "0.0.0.0", "--port", "8088"]
