from fastapi import FastAPI

import app.core.all_models  # noqa: F401

app = FastAPI(title="med-helper API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
