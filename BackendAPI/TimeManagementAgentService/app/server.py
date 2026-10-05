"""Development runner: psycopg async requires a selector loop on Windows."""
import asyncio
import os
import sys

import uvicorn

from .main import app


def main() -> None:
    # 8003 belongs to DietPlanService; the .NET API default for this service is 8004.
    port = int(os.getenv("TIME_MANAGEMENT_PORT", "8004"))
    config = uvicorn.Config(app, host="127.0.0.1", port=port, loop="none")
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
