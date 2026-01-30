# ./aiwolf-nlp-agent/Dockerfile
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.12-slim

COPY --from=uv_bin /uv /uvx /bin/

RUN apt-get update && apt-get install -y build-essential curl git && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# 標準的にプロジェクトルートの .venv を使用する
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 実行パスを通す
ENV PATH="/app/.venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]
