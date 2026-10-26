"""Run GM/console commands on mangosd through its Remote Admin port (127.0.0.1:3443).

    python tools/gm.py "account create mybot secret"
    python tools/gm.py "account set gmlevel mybot 3"

Login comes from RA_USER / RA_PASS, taken from the environment or else from server/.env.
"""
import os
import socket
import sys
import time
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def env(name, default=None):
    if name in os.environ:
        return os.environ[name]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name:
                return value.strip()
    return default


def recv_until_quiet(sock, quiet=0.5):
    sock.settimeout(quiet)
    data = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            return data.decode(errors="replace")
        if not chunk:
            return data.decode(errors="replace")
        data += chunk


def run(commands, host="127.0.0.1", port=3443):
    user = env("RA_USER", "ADMINISTRATOR")
    password = env("RA_PASS", "ADMINISTRATOR")
    with socket.create_connection((host, port), timeout=5) as sock:
        recv_until_quiet(sock)
        sock.sendall(f"{user}\r\n".encode())
        recv_until_quiet(sock)
        sock.sendall(f"{password}\r\n".encode())
        greeting = recv_until_quiet(sock)
        if "+" not in greeting and "Logged in" not in greeting:
            sys.exit(f"RA login failed: {greeting.strip()}")
        for cmd in commands:
            sock.sendall(f"{cmd}\r\n".encode())
            time.sleep(0.2)
            print(f"> {cmd}\n{recv_until_quiet(sock).strip()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run(sys.argv[1:])
