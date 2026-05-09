FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OFFLINE_ONLY=1 \
    MEMORYFEED_AI_PROVIDER=none \
    MEMORYFEED_DATA_DIR=/data

WORKDIR /app

COPY pyproject.toml README.md cli.py ./
COPY backend ./backend
COPY memoryfeed ./memoryfeed
COPY extension ./extension
COPY frontend ./frontend
COPY native ./native

RUN pip install --upgrade pip && pip install .

EXPOSE 7749
VOLUME ["/data"]

CMD ["memoryfeed", "serve", "--host", "0.0.0.0", "--port", "7749"]
