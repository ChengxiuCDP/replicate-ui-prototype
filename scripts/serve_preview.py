#!/usr/bin/env python3
"""Serve a prototype directory over loopback for local browser preview."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def create_server(directory: Path, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"preview directory does not exist: {directory}")
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    return ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        server = create_server(args.directory, args.host, args.port)
    except (OSError, ValueError) as error:
        print(f"preview failed: {error}", file=sys.stderr)
        return 1
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
