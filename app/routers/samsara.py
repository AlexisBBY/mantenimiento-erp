from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, samsara as samsara_client
from ..database import get_db
from ..auth import requiere_modulo

router = APIRouter(prefix="/api/samsara", tags=["samsara"], dependencies=[Depends(requiere_modulo("unidades"))])


@router.get("/vehiculos")
def listar_vehiculos_samsara():
    try:
        return samsara_client.listar_vehiculos()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error consultando Samsara: {e}")


@router.post("/sincronizar")
def sincronizar_con_samsara(db: Session = Depends(get_db)):
    unidades = crud.unidades_con_mapeo_samsara(db)
    ids = [u.samsara_vehicle_id for u in unidades]
    if not ids:
        return {"actualizadas": [], "sin_dato": [], "mensaje": "Ninguna unidad tiene configurado su ID de Samsara todavía."}
    try:
        odometros = samsara_client.obtener_odometros(ids)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error consultando Samsara: {e}")
    return crud.sincronizar_km_con_samsara(db, odometros)