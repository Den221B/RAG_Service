ARG BASE_IMG=nvidia/cuda:12.8.0-runtime-ubuntu22.04
FROM ${BASE_IMG}

ARG PYTHON_VERSION=3.11-slim
ARG PORT=8004

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-dev python3-pip && \
    ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python && \
    python -m pip install --upgrade pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]