from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, rooms, bookings

app = FastAPI(title="AiSpace")
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(bookings.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")