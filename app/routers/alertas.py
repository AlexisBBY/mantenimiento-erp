from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, models
from ..database import get_db
from ..auth import obtener_usuario_actual

router = APIRouter(prefix="/api/alertas", tags=["alertas"])


@router.get("/")
def obtener_alertas(db: Session = Depends(get_db), usuario: models.Usuario = Depends(obtener_usuario_actual)):
    """
    Junta unidades y llantas en estado 'proximo' o 'vencido'. Si el usuario
    no es admin, solo se muestran las alertas de los módulos a los que
    tiene acceso.
    """
    modulos_permitidos = {p.modulo for p in usuario.permisos} if not usuario.es_admin else None

    resultado = crud.obtener_alertas(db)

    if modulos_permitidos is not None:
        if "unidades" not in modulos_permitidos:
            resultado["unidades"] = []
        if "llantas" not in modulos_permitidos:
            resultado["llantas"] = []
        resultado["total"] = len(resultado["unidades"]) + len(resultado["llantas"])

    return resultado
