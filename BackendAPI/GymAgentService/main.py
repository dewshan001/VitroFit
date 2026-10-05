"""Development runner: psycopg async (the Postgres checkpointer) needs a selector
event loop on Windows, which `uvicorn src.api.app:app` does not use by default.

Start with:  python main.py
"""

import asyncio
import sys

import uvicorn

from src.api.app import app


# Loopback only: the service must never listen on a network interface. Only ASP.NET (same machine) calls it.
HOST = "127.0.0.1"
PORT = 8001


def main() -> None:
    config = uvicorn.Config(app, host=HOST, port=PORT, loop="none")
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
