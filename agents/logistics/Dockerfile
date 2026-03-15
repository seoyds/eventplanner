FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY shared/ ./shared/
COPY agents/logistics/ ./agents/logistics/
RUN uv sync --frozen --no-dev
EXPOSE 8008
CMD ["uv", "run", "python", "-m", "agents.logistics.main"]
