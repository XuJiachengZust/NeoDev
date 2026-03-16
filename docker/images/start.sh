#!/usr/bin/env bash
# NeoDev 内网一键启动（纯 docker，无需 docker-compose）
#
# 用法:
#   启动: bash start.sh
#   停止: bash start.sh stop
#   查看: bash start.sh status
#   清除（含数据）: bash start.sh clean
#
# 首次使用前先导入镜像: docker load -i neodev-all-images.tar
# 若报错「$'\r': 未找到命令」，先执行: sed -i 's/\r$//' start.sh
#
# 若出现「Cannot allocate memory」或 initdb/postgres 报错:
#   1) 本脚本已为 postgres 容器增加 --shm-size=256m，需先删掉旧容器和数据卷再重跑:
#      docker rm -f neodev-postgres && docker volume rm neodev-postgres-data
#   2) 若仍报错，再考虑加 swap（见下）或检查镜像是否损坏。
# 添加 swap 示例:
#   sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
#   sudo mkswap /swapfile && sudo swapon /swapfile
#   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

set -euo pipefail

# ── 配置（按需修改）─────────────────────────────────────────────
OPENAI_API_KEY="${OPENAI_API_KEY:-sk-your-key}"
OPENAI_BASE="${OPENAI_BASE:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
OPENAI_MODEL_CHAT="${OPENAI_MODEL_CHAT:-deepseek-v3.2}"
OPENAI_MODEL_EMBEDDING="${OPENAI_MODEL_EMBEDDING:-text-embedding-v3}"

PG_USER="postgres"
PG_PASS="postgres"
PG_DB="neodev"

NEO4J_USER="neo4j"
NEO4J_PASS="password123"

WEB_PORT="${WEB_PORT:-80}"
NETWORK="neodev-net"

# ── 函数 ───────────────────────────────────────────────────────
wait_healthy() {
    local name=$1 max=${2:-60}
    echo -n "  等待 $name 就绪"
    for i in $(seq 1 $max); do
        status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "missing")
        if [ "$status" = "healthy" ]; then
            echo " [OK]"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    echo " [超时]"
    echo "错误: $name 未能在 $((max*2)) 秒内就绪"
    docker logs --tail 20 "$name"
    exit 1
}

do_start() {
    echo "=== NeoDev 启动 ==="

    # 内存检查（PostgreSQL/Neo4j 初始化较吃内存，建议至少 2GB 可用）
    if command -v free >/dev/null 2>&1; then
        local avail_mb
        avail_mb=$(free -m | awk '/^Mem:/{print $7}')
        echo "  当前可用内存: ${avail_mb} MB"
        if [ "${avail_mb:-0}" -lt 1800 ] 2>/dev/null; then
            echo ""
            echo "  警告: 可用内存不足 2GB，PostgreSQL 初始化可能报 Cannot allocate memory。"
            echo "  建议添加 swap 后再执行本脚本，参见脚本顶部注释。"
            echo ""
            read -p "  是否仍继续启动? (y/N) " confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                echo "已取消"
                exit 1
            fi
        fi
    fi

    # 创建网络
    docker network inspect $NETWORK >/dev/null 2>&1 || \
        docker network create $NETWORK
    echo "[1/5] 网络 $NETWORK 就绪"

    # ── PostgreSQL ─────────────────────────────────────────────
    if docker ps -a --format '{{.Names}}' | grep -q '^neodev-postgres$'; then
        docker start neodev-postgres 2>/dev/null || true
    else
        docker run -d \
            --name neodev-postgres \
            --network $NETWORK \
            --restart unless-stopped \
            --shm-size=256m \
            -e POSTGRES_USER=$PG_USER \
            -e POSTGRES_PASSWORD=$PG_PASS \
            -e POSTGRES_DB=$PG_DB \
            -p 5432:5432 \
            -v neodev-postgres-data:/var/lib/postgresql/data \
            --health-cmd "pg_isready -U postgres" \
            --health-interval 5s \
            --health-timeout 5s \
            --health-retries 5 \
            neodev-postgres:latest
    fi
    echo "[2/5] PostgreSQL 已启动"
    wait_healthy neodev-postgres

    # ── Neo4j ──────────────────────────────────────────────────
    if docker ps -a --format '{{.Names}}' | grep -q '^neodev-neo4j$'; then
        docker start neodev-neo4j 2>/dev/null || true
    else
        docker run -d \
            --name neodev-neo4j \
            --network $NETWORK \
            --restart unless-stopped \
            -e NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASS} \
            -e 'NEO4J_PLUGINS=["apoc"]' \
            -e NEO4J_server_memory_heap_max__size=1G \
            -p 7474:7474 \
            -p 7687:7687 \
            -v neodev-neo4j-data:/data \
            -v neodev-neo4j-logs:/logs \
            --health-cmd "cypher-shell -u neo4j -p ${NEO4J_PASS} 'RETURN 1' || exit 1" \
            --health-interval 10s \
            --health-timeout 10s \
            --health-retries 5 \
            --health-start-period 30s \
            neo4j:5-community
    fi
    echo "[3/5] Neo4j 已启动"
    wait_healthy neodev-neo4j 30

    # ── API 后端 ───────────────────────────────────────────────
    if docker ps -a --format '{{.Names}}' | grep -q '^neodev-api$'; then
        docker start neodev-api 2>/dev/null || true
    else
        docker run -d \
            --name neodev-api \
            --network $NETWORK \
            --restart unless-stopped \
            -e DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@neodev-postgres:5432/${PG_DB}" \
            -e NEO4J_URI="bolt://neodev-neo4j:7687" \
            -e NEO4J_USER=$NEO4J_USER \
            -e NEO4J_PASSWORD=$NEO4J_PASS \
            -e OPENAI_API_KEY="$OPENAI_API_KEY" \
            -e OPENAI_BASE="$OPENAI_BASE" \
            -e OPENAI_MODEL_CHAT="$OPENAI_MODEL_CHAT" \
            -e OPENAI_MODEL_EMBEDDING="$OPENAI_MODEL_EMBEDDING" \
            -e AI_ANALYSIS_MAX_WORKERS=5 \
            -e REPO_CLONE_BASE=/data/repos \
            -e AGENT_SANDBOX_ROOT=/data/sandboxes \
            -v neodev-repo-data:/data/repos \
            -v neodev-sandbox-data:/data/sandboxes \
            neodev-api:latest
    fi
    echo "[4/5] API 后端已启动"

    # ── Nginx 前端 ─────────────────────────────────────────────
    if docker ps -a --format '{{.Names}}' | grep -q '^neodev-web$'; then
        docker start neodev-web 2>/dev/null || true
    else
        docker run -d \
            --name neodev-web \
            --network $NETWORK \
            --restart unless-stopped \
            -p ${WEB_PORT}:80 \
            neodev-web:latest
    fi
    echo "[5/5] Web 前端已启动"

    sleep 3
    echo ""
    echo "=== 全部启动完成 ==="
    echo "  前端:        http://localhost:${WEB_PORT}"
    echo "  Neo4j 控制台: http://localhost:7474"
    echo ""
    do_status
}

do_stop() {
    echo "=== 停止 NeoDev ==="
    for c in neodev-web neodev-api neodev-neo4j neodev-postgres; do
        docker stop $c 2>/dev/null && echo "  已停止 $c" || echo "  $c 未运行"
    done
}

do_status() {
    echo "=== 容器状态 ==="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
        --filter "name=neodev-" 2>/dev/null || echo "无运行中的 neodev 容器"
}

do_clean() {
    echo "=== 清除 NeoDev（含数据）==="
    read -p "确认删除所有容器和数据卷？(y/N) " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "已取消"
        exit 0
    fi
    for c in neodev-web neodev-api neodev-neo4j neodev-postgres; do
        docker rm -f $c 2>/dev/null || true
    done
    for v in neodev-postgres-data neodev-neo4j-data neodev-neo4j-logs neodev-repo-data neodev-sandbox-data; do
        docker volume rm $v 2>/dev/null || true
    done
    docker network rm $NETWORK 2>/dev/null || true
    echo "已全部清除"
}

case "${1:-}" in
    stop)   do_stop ;;
    status) do_status ;;
    clean)  do_clean ;;
    *)      do_start ;;
esac
