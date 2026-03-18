# NeoDev API 后端镜像
FROM python:3.11-slim

# 替换 APT 源为阿里云镜像（加速国内构建）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        git openssh-client libpq-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
        -r requirements.txt \
    && pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
        psycopg[binary] psycopg_pool

COPY src/ ./src/
COPY docker/migrations/ ./docker/migrations/

RUN mkdir -p /data/repos /data/sandboxes /data/requirement_docs

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    REPO_CLONE_BASE=/data/repos \
    AGENT_SANDBOX_ROOT=/data/sandboxes

EXPOSE 8000

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
