FROM ghcr.io/astral-sh/uv:0.13.0 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./backend/
COPY backend/src ./backend/src
COPY backend/alembic.ini ./backend/
COPY backend/migrations ./backend/migrations
COPY backend/config ./backend/config
COPY sql ./sql
RUN uv sync --project backend --locked --no-dev
EXPOSE 8000
CMD ["backend/.venv/bin/uvicorn", "stocgain.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
