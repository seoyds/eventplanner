FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY shared/ ./shared/
COPY agents/accessibility/ ./agents/accessibility/
RUN uv sync --frozen --no-dev
EXPOSE 8006
CMD ["uv", "run", "python", "-m", "agents.accessibility.main"]
