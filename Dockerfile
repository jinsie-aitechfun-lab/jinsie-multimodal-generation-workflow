FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN set -eux; \
    found=0; \
    for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources; do \
        [ -f "$source_file" ] || continue; \
        sed -i \
            -e 's|http://deb\.debian\.org|https://deb.debian.org|g' \
            -e 's|http://security\.debian\.org|https://security.debian.org|g' \
            "$source_file"; \
        found=1; \
    done; \
    [ "$found" -eq 1 ]

RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
        ffmpeg \
        fontconfig \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY assets/samples ./assets/samples

RUN mkdir -p /app/assets/mock

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8004}"]
