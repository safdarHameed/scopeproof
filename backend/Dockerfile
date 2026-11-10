FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.9.9
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN useradd --create-home scopeproof && mkdir -p storage/uploads && chown -R scopeproof:scopeproof /app
USER scopeproof
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000"]
