from fastapi import FastAPI

app = FastAPI(title="AiSpace")

@app.get("/health")
def health():
    return {"status": "ok"}
