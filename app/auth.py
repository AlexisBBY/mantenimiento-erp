"""
Autenticación simple por cookie firmada (sin JWT ni servicios externos).

- Las contraseñas se guardan con hash bcrypt (passlib), nunca en texto plano.
- Al hacer login se firma el id de usuario con itsdangerous y se guarda en
  una cookie HttpOnly. No se necesita base de datos de sesiones ni Redis.
- Cada endpoint protegido depende de `requiere_modulo("nombre_modulo")`,
  que revisa si el usuario logueado es admin (ve todo) o tiene permiso
  explícito sobre ese módulo.

Variable de entorno SECRET_KEY: en producción (Render) definan una propia;
si no se define, se usa una de desarrollo (no usar tal cual en producción).
"""
import os
import datetime
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from . import models
from .database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-cambiar-en-produccion")
COOKIE_NAME = "session"
COOKIE_MAX_AGE_SEGUNDOS = 60 * 60 * 24 * 7  # 7 días

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="session-cookie")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def crear_token_sesion(usuario_id: int) -> str:
    return serializer.dumps({"usuario_id": usuario_id})


def leer_token_sesion(token: str) -> int | None:
    try:
        data = serializer.loads(token, max_age=COOKIE_MAX_AGE_SEGUNDOS)
        return data.get("usuario_id")
    except (BadSignature, SignatureExpired):
        return None


def obtener_usuario_actual(request: Request, db: Session = Depends(get_db)) -> models.Usuario:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="No has iniciado sesión")

    usuario_id = leer_token_sesion(token)
    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    return usuario


def requiere_modulo(modulo: str):
    """
    Devuelve una dependencia de FastAPI que exige que el usuario logueado
    sea admin, o tenga permiso explícito sobre `modulo`.
    """
    def _dependencia(usuario: models.Usuario = Depends(obtener_usuario_actual)) -> models.Usuario:
        if usuario.es_admin:
            return usuario
        modulos_permitidos = {p.modulo for p in usuario.permisos}
        if modulo not in modulos_permitidos:
            raise HTTPException(status_code=403, detail=f"No tienes acceso al módulo '{modulo}'")
        return usuario

    return _dependencia


def requiere_admin(usuario: models.Usuario = Depends(obtener_usuario_actual)) -> models.Usuario:
    if not usuario.es_admin:
        raise HTTPException(status_code=403, detail="Solo un administrador puede hacer esto")
    return usuario


def asegurar_admin_inicial(db: Session):
    """
    Si no existe ningún usuario, crea un admin por defecto para poder
    entrar la primera vez. Cambiar la contraseña de inmediato.
    """
    if db.query(models.Usuario).count() == 0:
        admin = models.Usuario(
            username="admin",
            password_hash=hash_password("admin123"),
            nombre_completo="Administrador",
            es_admin=1,
            activo=1,
        )
        db.add(admin)
        db.commit()
        print(
            "\n*** Se creó un usuario admin por defecto ***\n"
            "    usuario: admin\n"
            "    contraseña: admin123\n"
            "    Cámbiala en cuanto entres.\n"
        )
