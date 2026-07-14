from fastapi import FastAPI

app = FastAPI(title="AgentDesk API")


@app.get("/health")
async def health():
    return {"status": "ok"}
