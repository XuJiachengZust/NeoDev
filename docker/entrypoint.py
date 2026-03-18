#!/usr/bin/env python3
"""容器启动入口：自动检测并适配内网 SSL 代理"""
import ssl, socket, os, sys
from urllib.parse import urlparse


def fix_ssl_if_needed():
    base = os.environ.get("OPENAI_BASE", "")
    if not base:
        return

    parsed = urlparse(base if "://" in base else f"https://{base}")
    host = parsed.hostname
    port = parsed.port or 443
    if not host:
        return

    # 默认验证能通过则无需修复
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as s:
                pass
        return
    except Exception:
        pass

    # SSL 验证失败，全局跳过验证
    print(f"[entrypoint] SSL 验证失败 ({host}:{port})，已全局跳过 SSL 验证")
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ["PYTHONHTTPSVERIFY"] = "0"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["SSL_CERT_FILE"] = ""


if __name__ == "__main__":
    fix_ssl_if_needed()
    os.execvp(sys.argv[1], sys.argv[1:])
