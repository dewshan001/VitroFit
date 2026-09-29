"""Development runner: psycopg async (the Postgres checkpointer) needs a selector
event loop on Windows, which `uvicorn main:app` does not use by default.

Start with:  python server.py
"""

import asyncio
import sys

import uvicorn

from main import app


def main() -> None:
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, loop="none")
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
