# --- Build Stage ---
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.12-slim

# uvバイナリをコピー
COPY --from=uv_bin /uv /uvx /bin/

# コンテナ内でのキャッシュ効率を高めるための設定
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# 先に依存関係ファイルのみをコピーしてインストール（キャッシュ活用）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# ソースコードをコピー
COPY . .

# プロジェクト自体をインストール（srcレイアウトなどの場合も考慮）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 実行
# uv run を通じて実行することで、適切な環境で実行されます
# CMD ["uv", "run", "python", "src/main.py"]
# 待機状態にしておく（デバッグ用）
CMD ["uv", "run", "tail", "-f", "/dev/null"]
