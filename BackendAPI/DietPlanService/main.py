# DietPlanService/main.py
"""Entry point. `uvicorn main:app --port 8003` (how VitroFit.API launches this
service) or `python main.py`. The application itself is built in src/api/app.py."""
import os

from src.api.app import app  # noqa: F401 - re-exported for uvicorn

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8003")))
