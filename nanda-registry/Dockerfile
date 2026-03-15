FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Clone the NANDA Index repo
RUN apt-get update && apt-get install -y git && \
    git clone https://github.com/projnanda/nanda-index.git . && \
    uv sync --frozen && \
    apt-get remove -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

EXPOSE 6900

CMD ["uv", "run", "python", "registry.py"]
