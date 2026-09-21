"""Does an idle chat WebSocket hold a database connection?

Starts the API (real code, real pooled engine, real hosted DB) on a local port,
opens N authenticated WebSockets that just sit there, then times an ordinary HTTP
request from someone else. With the default pool (5 + 10 overflow) a server that
keeps one connection checked out per idle socket stalls every other request as
soon as more than ~15 people have a chat open.

python -m qa.pool_probe <backend_dir> <port> [sockets]
Creates throw-away qa-pool-*@example.com users (remove with qa/leak_audit.py).
"""
import asyncio
import os
import subprocess
import sys
import time
import uuid

import httpx
import websockets


def main(backend_dir: str, port: int, n_sockets: int = 24) -> None:
    env = {**os.environ, "ENABLE_LEGACY_AUTH": "true", "RATE_LIMIT_ENABLED": "false", "APP_ENV": "local"}
    py = sys.executable
    proc = subprocess.Popen([py, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"], cwd=backend_dir, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(base + "/health", timeout=2).status_code == 200:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        users = []
        for i in range(n_sockets + 1):
            r = httpx.post(base + "/auth/signup", json={"email": f"qa-pool-{uuid.uuid4().hex[:8]}@example.com", "password": "password123"}, timeout=30)
            r.raise_for_status()
            users.append(r.json()["access_token"])
        print(f"created {len(users)} users", flush=True)

        async def hold():
            socks = []
            for tok in users[:n_sockets]:
                try:
                    socks.append(await asyncio.wait_for(websockets.connect(f"ws://127.0.0.1:{port}/ws/chat?token={tok}"), 40))
                except Exception as e:  # noqa: BLE001
                    print("  socket failed:", type(e).__name__, flush=True)
            await asyncio.sleep(3)
            t0 = time.time()
            try:
                async with httpx.AsyncClient(timeout=45) as c:
                    r = await c.get(base + "/account/me", headers={"Authorization": f"Bearer {users[-1]}"})
                code = r.status_code
            except Exception as e:  # noqa: BLE001
                code = type(e).__name__
            elapsed = time.time() - t0
            print(f"{len(socks)} idle sockets open -> GET /account/me: {code} in {elapsed:.1f}s", flush=True)
            for s in socks:
                await s.close()

        asyncio.run(hold())
    finally:
        proc.terminate()
        try:
            proc.wait(15)
        except Exception:  # noqa: BLE001
            proc.kill()


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 24)
