FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY shared/ ./shared/
COPY agents/budget/ ./agents/budget/
RUN uv sync --frozen --no-dev
EXPOSE 8003
CMD ["uv", "run", "python", "-m", "agents.budget.main"]
