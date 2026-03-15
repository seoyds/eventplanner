FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace root
COPY pyproject.toml uv.lock ./

# Copy shared library (needed by all)
COPY shared/ ./shared/

# Copy all agent pyproject.toml stubs (needed for workspace resolution)
COPY agents/venue/pyproject.toml ./agents/venue/pyproject.toml
COPY agents/weather/pyproject.toml ./agents/weather/pyproject.toml
COPY agents/budget/pyproject.toml ./agents/budget/pyproject.toml
COPY agents/menu/pyproject.toml ./agents/menu/pyproject.toml
COPY agents/activity/pyproject.toml ./agents/activity/pyproject.toml
COPY agents/accessibility/pyproject.toml ./agents/accessibility/pyproject.toml
COPY agents/theme/pyproject.toml ./agents/theme/pyproject.toml
COPY agents/logistics/pyproject.toml ./agents/logistics/pyproject.toml
COPY agents/communication/pyproject.toml ./agents/communication/pyproject.toml
COPY agents/supplies/pyproject.toml ./agents/supplies/pyproject.toml
COPY conductor/pyproject.toml ./conductor/pyproject.toml

# Copy stub __init__.py for workspace members that need it
RUN for d in agents/venue agents/weather agents/budget agents/menu agents/activity agents/accessibility agents/theme agents/logistics agents/communication agents/supplies conductor conductor/tools; do mkdir -p $d && touch $d/__init__.py; done

# Now copy this agent's actual code (overwrites stubs)
COPY agents/menu/ ./agents/menu/

RUN uv sync --no-dev --all-packages --no-install-workspace

EXPOSE 8004
CMD ["uv", "run", "python", "-m", "agents.menu.main"]
