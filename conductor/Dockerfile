FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY shared/ ./shared/
COPY conductor/ ./conductor/
RUN uv sync --frozen --no-dev
EXPOSE 8000
CMD ["uv", "run", "python", "-m", "conductor.main"]
