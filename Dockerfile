FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

RUN uv venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv pip install --no-cache-dir -r pyproject.toml

COPY . .

FROM python:3.13-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN useradd -m appuser

RUN mkdir -p /app/celerybeat \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app/celerybeat \
    && chown -R appuser:appuser /app/staticfiles

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8002

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8002", "--workers", "3"]