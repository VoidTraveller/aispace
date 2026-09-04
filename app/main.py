from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, rooms, bookings

app = FastAPI(title="AiSpace")
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(bookings.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI's automatic Pydantic validation errors normally come back as an array
    of {loc, msg, type} objects, in English, with an internal "Value error, " prefix
    on our own custom validator messages -- this flattens them into one clean string
    (in whatever language the underlying message actually is, e.g. our Russian
    field_validator text) so the frontend can display it directly."""
    messages = [error["msg"].removeprefix("Value error, ") for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

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