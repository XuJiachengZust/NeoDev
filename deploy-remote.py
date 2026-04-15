#!/usr/bin/env python3
"""
NeoDev 远程 Docker 部署脚本

一键完成: 本地构建 -> 导出镜像 -> 上传远程 -> 加载并重启容器

用法:
    python deploy-remote.py                # 部署后端 API（默认）
    python deploy-remote.py --web          # 部署前端 Web
    python deploy-remote.py --all          # 部署前端 + 后端
    python deploy-remote.py --full         # 部署全部自建镜像（api + web + postgres）
    python deploy-remote.py --no-cache     # 构建时不使用 Docker 缓存
    python deploy-remote.py --skip-build   # 跳过构建，仅上传已有 tar 并部署
    python deploy-remote.py --restart-only # 不上传，仅重启远程容器
    python deploy-remote.py --status       # 查看远程容器状态
    python deploy-remote.py --logs api     # 查看远程服务日志
"""

import argparse
import os
import subprocess
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 远程服务器配置 ──────────────────────────────────────────────────
# 所有敏感信息必须通过环境变量注入，禁止在仓库中硬编码。
REMOTE_HOST = os.getenv("NEODEV_REMOTE_HOST", "10.50.3.149")
REMOTE_USER = os.getenv("NEODEV_REMOTE_USER", "root")
REMOTE_PASSWORD = os.getenv("NEODEV_REMOTE_PASSWORD")
REMOTE_DIR = os.getenv("NEODEV_REMOTE_DIR", "/root/neodev")

# ── 本地路径 ────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TAR_DIR = os.path.join(PROJECT_ROOT, "docker", "images")

# ── 服务 -> 镜像 & 容器名映射 ──────────────────────────────────────
SERVICE_META = {
    "api": {"image": "neodev-api:latest", "container": "neodev-api", "label": "后端 API"},
    "web": {"image": "neodev-web:latest", "container": "neodev-web", "label": "前端 Web"},
    "postgres": {"image": "neodev-postgres:latest", "container": "neodev-postgres", "label": "PostgreSQL"},
}

# 快捷分组
SERVICE_GROUPS = {
    "api":  ["api"],
    "web":  ["web"],
    "all":  ["api", "web"],
    "full": ["api", "web", "postgres"],
}

# ═══════════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════════

def log(msg: str):
    print(f"\n{'=' * 60}\n  {msg}\n{'=' * 60}")


def run(cmd: str, *, cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_ROOT,
                            capture_output=False, text=True)
    if check and result.returncode != 0:
        print(f"\n  [FAIL] 命令退出码 {result.returncode}")
        sys.exit(1)
    return result


def get_ssh_client():
    try:
        import paramiko
    except ImportError:
        print("缺少 paramiko，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko

    if not REMOTE_PASSWORD:
        print("缺少环境变量 NEODEV_REMOTE_PASSWORD，已拒绝使用未配置密码的远程部署。")
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"  连接 {REMOTE_USER}@{REMOTE_HOST} ...")
    client.connect(
        REMOTE_HOST,
        username=REMOTE_USER,
        password=REMOTE_PASSWORD,
        timeout=30,
        banner_timeout=60,
        auth_timeout=60,
        look_for_keys=False,
        allow_agent=False,
    )
    print("  SSH 连接成功")
    return client


def ssh_exec(client, cmd: str, *, check: bool = True) -> str:
    print(f"  [remote] $ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=300)
    out_lines = []
    for line in stdout:
        stripped = line.rstrip("\n")
        print(f"    {stripped}")
        out_lines.append(stripped)
    err = stderr.read().decode().strip()
    if err:
        print(f"    [stderr] {err}")
    exit_code = stdout.channel.recv_exit_status()
    if check and exit_code != 0:
        print(f"\n  [FAIL] 远程命令退出码 {exit_code}")
        sys.exit(1)
    return "\n".join(out_lines)


def sftp_upload(client, local_path: str, remote_path: str):
    file_size = os.path.getsize(local_path)
    size_mb = file_size / 1024 / 1024
    print(f"  本地文件: {size_mb:.1f} MB")
    print(f"  目标路径: {remote_path}")

    sftp = client.open_sftp()
    start = time.time()
    last_print = [0]

    def progress(transferred: int, total: int):
        pct = transferred * 100 / total
        now = time.time()
        if now - last_print[0] < 2 and pct < 100:
            return
        last_print[0] = now
        elapsed = now - start
        speed = (transferred / 1024 / 1024) / elapsed if elapsed > 0 else 0
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
        sys.stdout.write(
            f"\r  [{bar}] {pct:5.1f}%  "
            f"{transferred / 1024 / 1024:.1f}/{size_mb:.1f} MB  "
            f"{speed:.1f} MB/s   "
        )
        sys.stdout.flush()

    sftp.put(local_path, remote_path, callback=progress)
    elapsed = time.time() - start
    avg_speed = size_mb / elapsed if elapsed > 0 else 0
    print(f"\n  上传完成! 耗时 {elapsed:.1f}s, 平均 {avg_speed:.1f} MB/s")
    sftp.close()


def service_labels(services: list[str]) -> str:
    return ", ".join(SERVICE_META[s]["label"] for s in services)


# ═══════════════════════════════════════════════════════════════════
#  部署步骤
# ═══════════════════════════════════════════════════════════════════

def step_build(services: list[str], no_cache: bool = False):
    log(f"[1/4] 本地构建: {service_labels(services)}")
    cache_flag = " --no-cache" if no_cache else ""
    run(f"docker compose build{cache_flag} {' '.join(services)}")


def step_save(services: list[str]) -> str:
    log("[2/4] 导出镜像为 tar")
    os.makedirs(TAR_DIR, exist_ok=True)
    images = [SERVICE_META[s]["image"] for s in services]

    if services == ["api"]:
        tar_name = "neodev-api-latest.tar"
    elif services == ["web"]:
        tar_name = "neodev-web-latest.tar"
    else:
        tar_name = "neodev-update.tar"

    tar_path = os.path.join(TAR_DIR, tar_name)
    run(f"docker save {' '.join(images)} -o \"{tar_path}\"")
    size_mb = os.path.getsize(tar_path) / 1024 / 1024
    print(f"  已导出: {tar_name} ({size_mb:.1f} MB)")
    return tar_path


def step_upload(tar_path: str, client) -> str:
    log("[3/4] 上传镜像到远程服务器")
    remote_tar = f"{REMOTE_DIR}/{os.path.basename(tar_path)}"
    sftp_upload(client, tar_path, remote_tar)
    return remote_tar


def step_deploy(client, remote_tar: str, services: list[str]):
    log(f"[4/4] 远程部署: {service_labels(services)}")

    print("\n  --- 加载镜像 ---")
    ssh_exec(client, f"docker load -i {remote_tar}")

    print("\n  --- 重启服务 ---")
    svc_list = " ".join(services)
    ssh_exec(client, f"cd {REMOTE_DIR} && docker compose up -d {svc_list}")

    print("\n  --- 清理旧 tar ---")
    ssh_exec(client, f"rm -f {remote_tar}", check=False)

    print("\n  --- 等待服务启动 (5s) ---")
    time.sleep(5)

    print("\n  --- 容器状态 ---")
    ssh_exec(client, f"cd {REMOTE_DIR} && docker compose ps")

    for svc in services:
        container = SERVICE_META[svc]["container"]
        label = SERVICE_META[svc]["label"]
        print(f"\n  --- {label} 最近日志 ({container}) ---")
        ssh_exec(client, f"docker logs --tail=10 {container}", check=False)


def step_restart_only(client, services: list[str]):
    log(f"重启远程容器: {service_labels(services)}")
    svc_list = " ".join(services)
    ssh_exec(client, f"cd {REMOTE_DIR} && docker compose restart {svc_list}")
    time.sleep(5)
    ssh_exec(client, f"cd {REMOTE_DIR} && docker compose ps")
    for svc in services:
        container = SERVICE_META[svc]["container"]
        print(f"\n  --- {SERVICE_META[svc]['label']} 日志 ---")
        ssh_exec(client, f"docker logs --tail=10 {container}", check=False)


def step_status(client):
    log("远程容器状态")
    ssh_exec(client, f"cd {REMOTE_DIR} && docker compose ps")
    ssh_exec(client, "docker stats --no-stream --format "
             "'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}' "
             "$(docker ps -q --filter name=neodev-)", check=False)


def step_logs(client, services: list[str], lines: int = 30):
    for svc in services:
        container = SERVICE_META[svc]["container"]
        log(f"日志: {SERVICE_META[svc]['label']} ({container})")
        ssh_exec(client, f"docker logs --tail={lines} {container}", check=False)


# ═══════════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NeoDev 远程 Docker 部署",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "快捷示例:\n"
            "  deploy-remote.py              仅后端 API\n"
            "  deploy-remote.py --web        仅前端 Web\n"
            "  deploy-remote.py --all        前端 + 后端\n"
            "  deploy-remote.py --full       全部镜像 (api+web+postgres)\n"
            "  deploy-remote.py --status     查看远程状态\n"
            "  deploy-remote.py --logs web   查看前端日志\n"
        ),
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--web", action="store_true",
                       help="仅部署前端 Web")
    group.add_argument("--all", action="store_true",
                       help="部署前端 + 后端")
    group.add_argument("--full", action="store_true",
                       help="部署全部自建镜像 (api + web + postgres)")
    group.add_argument("--services", nargs="+",
                       choices=list(SERVICE_META.keys()),
                       help="自定义指定服务列表")

    parser.add_argument("--no-cache", action="store_true",
                        help="Docker 构建不使用缓存")
    parser.add_argument("--skip-build", action="store_true",
                        help="跳过构建，直接上传已有 tar 并部署")
    parser.add_argument("--restart-only", action="store_true",
                        help="不上传，仅重启远程容器")
    parser.add_argument("--status", action="store_true",
                        help="查看远程容器状态和资源占用")
    parser.add_argument("--logs", nargs="*", default=None, metavar="SVC",
                        help="查看远程服务日志 (默认 api)")
    parser.add_argument("--log-lines", type=int, default=30,
                        help="日志行数 (默认 30)")

    args = parser.parse_args()

    # 解析目标服务
    if args.services:
        services = args.services
    elif args.web:
        services = SERVICE_GROUPS["web"]
    elif args.all:
        services = SERVICE_GROUPS["all"]
    elif args.full:
        services = SERVICE_GROUPS["full"]
    else:
        services = SERVICE_GROUPS["api"]

    total_start = time.time()
    print(f"\n  NeoDev 部署  |  目标: {REMOTE_HOST}  |  服务: {service_labels(services)}")
    print(f"  {'=' * 56}")

    client = get_ssh_client()

    try:
        if args.status:
            step_status(client)
        elif args.logs is not None:
            log_svcs = args.logs if args.logs else ["api"]
            step_logs(client, log_svcs, lines=args.log_lines)
        elif args.restart_only:
            step_restart_only(client, services)
        else:
            if not args.skip_build:
                step_build(services, no_cache=args.no_cache)
            tar_path = step_save(services)
            remote_tar = step_upload(tar_path, client)
            step_deploy(client, remote_tar, services)
    finally:
        client.close()

    elapsed = time.time() - total_start
    log(f"完成! 总耗时 {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print(f"  访问: http://{REMOTE_HOST}")
    print()


if __name__ == "__main__":
    main()
