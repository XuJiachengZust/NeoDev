#!/usr/bin/env bash
# NeoDev 离线部署辅助脚本
# 在有网络的机器上运行此脚本，导出所有镜像为 tar 包
# 然后将 tar 包和项目文件拷贝到内网机器导入
#
# 用法:
#   构建并导出: bash docker/deploy-offline.sh export
#   内网导入:   bash docker/deploy-offline.sh import

set -euo pipefail

EXPORT_DIR="docker/images"

export_images() {
    echo "=== 步骤 1/3: 构建应用镜像 ==="
    docker compose build

    echo "=== 步骤 2/3: 拉取基础镜像 ==="
    docker pull pgvector/pgvector:0.8.0-pg16
    docker pull neo4j:5-community
    docker pull nginx:1.27-alpine

    echo "=== 步骤 3/3: 导出为 tar 包 ==="
    mkdir -p "$EXPORT_DIR"

    # 获取 compose 构建的镜像名
    API_IMAGE=$(docker compose images api --format json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['Repository'] + ':' + json.load(sys.stdin)[0]['Tag'])" 2>/dev/null || echo "")
    WEB_IMAGE=$(docker compose images web --format json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['Repository'] + ':' + json.load(sys.stdin)[0]['Tag'])" 2>/dev/null || echo "")

    # 保存所有镜像到单个 tar
    echo "  导出中..."
    docker save \
        pgvector/pgvector:0.8.0-pg16 \
        neo4j:5-community \
        nginx:1.27-alpine \
        ${API_IMAGE:+$API_IMAGE} \
        ${WEB_IMAGE:+$WEB_IMAGE} \
        -o "$EXPORT_DIR/neodev-all-images.tar"

    echo ""
    echo "=== 导出完成 ==="
    echo "文件: $EXPORT_DIR/neodev-all-images.tar"
    ls -lh "$EXPORT_DIR/neodev-all-images.tar"
    echo ""
    echo "部署到内网:"
    echo "  1. 将整个项目目录和 $EXPORT_DIR/neodev-all-images.tar 拷贝到目标机器"
    echo "  2. 在目标机器执行: bash docker/deploy-offline.sh import"
    echo "  3. 启动服务: docker compose up -d"
}

import_images() {
    if [ ! -f "$EXPORT_DIR/neodev-all-images.tar" ]; then
        echo "错误: 找不到 $EXPORT_DIR/neodev-all-images.tar"
        echo "请先在有网络的机器上执行: bash docker/deploy-offline.sh export"
        exit 1
    fi

    echo "=== 导入 Docker 镜像 ==="
    docker load -i "$EXPORT_DIR/neodev-all-images.tar"

    echo ""
    echo "=== 导入完成 ==="
    echo "启动服务:"
    echo "  1. 复制 .env.example 为 .env 并修改配置"
    echo "  2. docker compose up -d"
    echo "  3. 访问 http://<服务器IP>:${WEB_PORT:-80}"
}

case "${1:-}" in
    export) export_images ;;
    import) import_images ;;
    *)
        echo "用法: bash docker/deploy-offline.sh [export|import]"
        echo "  export  在有网络的机器上构建并导出镜像"
        echo "  import  在内网机器上导入镜像"
        exit 1
        ;;
esac
