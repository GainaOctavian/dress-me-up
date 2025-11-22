FROM --platform=linux/amd64 python:3.13.0-slim

ENV PYTHONPATH="${PYTHONPATH}:/."

# Install CA certificates and dependencies required for TLS
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates openssl netcat-openbsd \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY app/backend/common /app/backend/common
COPY app/backend/api /app/backend/api
RUN pip install --upgrade pip
RUN pip install -r app/backend/api/requirements.txt

EXPOSE 8080

CMD ["python3", "app/backend/api/src/main.py"]