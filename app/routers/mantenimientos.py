from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, schemas
from ..database import get_db
from ..auth import requiere_modulo

router = APIRouter(prefix="/api/mantenimientos", tags=["mantenimientos"], dependencies=[Depends(requiere_modulo("mantenimientos"))])


@router.post("/", response_model=schemas.MantenimientoOut)
def crear_mantenimiento(mant: schemas.MantenimientoCreate, db: Session = Depends(get_db)):
    unidad = crud.obtener_unidad(db, mant.unidad_id)
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    return crud.crear_mantenimiento(db, mant)


@router.get("/", response_model=List[schemas.MantenimientoOut])
def listar_mantenimientos(unidad_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.listar_mantenimientos(db, unidad_id)
