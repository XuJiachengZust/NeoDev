#!/bin/bash
set -e

# 内网 SSL 代理自动适配
# 从 OPENAI_BASE 提取目标主机，探测是否存在代理证书问题，自动修复
if [ -n "$OPENAI_BASE" ]; then
    python3 - <<'PYEOF'
import ssl, socket, os, subprocess, sys
from urllib.parse import urlparse

base = os.environ.get("OPENAI_BASE", "")
parsed = urlparse(base if "://" in base else f"https://{base}")
host = parsed.hostname
port = parsed.port or 443

if not host:
    sys.exit(0)

# 先用默认验证测试，如果正常就不需要任何处理
try:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as s:
            pass
    sys.exit(0)
except Exception:
    pass

# SSL 验证失败，提取代理证书
print(f"[entrypoint] SSL 验证失败，正在提取代理证书 ({host}:{port})...")
try:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as s:
            der = s.getpeercert(binary_form=True)

    # 转换 DER -> PEM 并安装
    pem_path = "/usr/local/share/ca-certificates/proxy-ca.crt"
    result = subprocess.run(
        ["openssl", "x509", "-inform", "DER", "-outform", "PEM"],
        input=der, capture_output=True
    )
    with open(pem_path, "wb") as f:
        f.write(result.stdout)

    subprocess.run(["update-ca-certificates"], capture_output=True)

    # 降低 SECLEVEL 以兼容弱密钥代理证书
    cnf = "/etc/ssl/openssl.cnf"
    with open(cnf, "r") as f:
        content = f.read()
    content = content.replace("SECLEVEL=2", "SECLEVEL=1")
    with open(cnf, "w") as f:
        f.write(content)

    print("[entrypoint] 代理 CA 证书已安装，SECLEVEL 已降为 1")
except Exception as e:
    print(f"[entrypoint] 代理证书自动安装失败: {e}，继续启动...")
PYEOF
fi

exec "$@"
