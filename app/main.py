from fastapi import FastAPI

from app.routers import auth, rooms, bookings

app = FastAPI(title="AiSpace")
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(bookings.router)

@app.get("/health")
def health():
    return {"status": "ok"}
