ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

ARG APT_MIRROR=https://mirrors.aliyun.com/debian
ARG APT_SECURITY_MIRROR=https://mirrors.aliyun.com/debian-security
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg may require libpq when installed from source; keep the image portable.
# tesseract 用于上传图片的 OCR 文字识别（AI 可读取图片中的文字）。
# The mirrors are build-time arguments so deployments in mainland China can
# use a nearby package source without changing the application image contract.
RUN set -eux; \
    find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print0 \
      | xargs -0 -r sed -i \
        -e "s#https\?://deb.debian.org/debian-security#${APT_SECURITY_MIRROR}#g" \
        -e "s#https\?://deb.debian.org/debian#${APT_MIRROR}#g"; \
    apt-get update \
    && apt-get install -y --no-install-recommends libpq5 tesseract-ocr tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --index-url "${PIP_INDEX_URL}" --upgrade pip \
    && pip install --index-url "${PIP_INDEX_URL}" -r requirements.txt

COPY . .
