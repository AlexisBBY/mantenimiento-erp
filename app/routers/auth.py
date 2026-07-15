from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models
from ..database import get_db
from ..auth import (
    verificar_password, crear_token_sesion, obtener_usuario_actual,
    requiere_admin, COOKIE_NAME, COOKIE_MAX_AGE_SEGUNDOS, hash_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(datos: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    usuario = crud.obtener_usuario_por_username(db, datos.username)
    if not usuario or not usuario.activo or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    token = crear_token_sesion(usuario.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SEGUNDOS,
        httponly=True,
        samesite="lax",
    )
    return crud.usuario_a_schema(usuario)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=schemas.UsuarioOut)
def me(usuario: models.Usuario = Depends(obtener_usuario_actual)):
    return crud.usuario_a_schema(usuario)


@router.post("/cambiar-password")
def cambiar_password(
    datos: schemas.CambiarPassword,
    usuario: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    if not verificar_password(datos.password_actual, usuario.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    usuario.password_hash = hash_password(datos.password_nueva)
    db.commit()
    return {"ok": True}


# ---------- Administración de usuarios (solo admin) ----------

usuarios_router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@usuarios_router.get("/", response_model=List[schemas.UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _admin: models.Usuario = Depends(requiere_admin)):
    return [crud.usuario_a_schema(u) for u in crud.listar_usuarios(db)]


@usuarios_router.post("/", response_model=schemas.UsuarioOut)
def crear_usuario(
    datos: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requiere_admin),
):
    if crud.obtener_usuario_por_username(db, datos.username):
        raise HTTPException(status_code=400, detail="Ese usuario ya existe")
    usuario = crud.crear_usuario(db, datos)
    return crud.usuario_a_schema(usuario)


@usuarios_router.patch("/{usuario_id}/permisos", response_model=schemas.UsuarioOut)
def actualizar_permisos(
    usuario_id: int,
    datos: schemas.PermisosUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requiere_admin),
):
    usuario = crud.actualizar_permisos(db, usuario_id, datos.modulos_permitidos)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return crud.usuario_a_schema(usuario)


@usuarios_router.post("/{usuario_id}/desactivar", response_model=schemas.UsuarioOut)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requiere_admin),
):
    usuario = crud.desactivar_usuario(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return crud.usuario_a_schema(usuario)


@usuarios_router.get("/modulos-disponibles")
def modulos_disponibles():
    return models.MODULOS_DISPONIBLES
