from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

from .database import Base, engine, SessionLocal
from .routers import unidades, mantenimientos, importar, llantas, auth as auth_router, alertas
from .auth import asegurar_admin_inicial

Base.metadata.create_all(bind=engine)

# Crea un usuario admin por defecto si la base de datos está vacía de usuarios
with SessionLocal() as _db:
    asegurar_admin_inicial(_db)

app = FastAPI(title="Módulo de Mantenimiento - ERP")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.include_router(auth_router.router)
app.include_router(auth_router.usuarios_router)
app.include_router(unidades.router)
app.include_router(mantenimientos.router)
app.include_router(importar.router)
app.include_router(llantas.router)
app.include_router(alertas.router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
