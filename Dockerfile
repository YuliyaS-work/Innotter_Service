FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

FROM python:3.13-slim AS production

WORKDIR /app

RUN useradd -m appuser
USER appuser

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app /app

EXPOSE 8002

CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]
RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

FROM python:3.13-slim AS production

WORKDIR /app

RUN useradd -m appuser
USER appuser

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app /app

EXPOSE 8002

CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]