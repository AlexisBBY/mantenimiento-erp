from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models
from ..database import get_db
from ..auth import requiere_modulo

router = APIRouter(prefix="/api/unidades", tags=["unidades"], dependencies=[Depends(requiere_modulo("unidades"))])


@router.post("/", response_model=schemas.UnidadOut)
def crear_unidad(unidad: schemas.UnidadCreate, db: Session = Depends(get_db)):
    existente = db.query(models.Unidad).filter_by(
        economico=unidad.economico
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ese económico ya existe")
    return crud.crear_unidad(db, unidad)


@router.get("/", response_model=List[schemas.UnidadEstado])
def listar_unidades(db: Session = Depends(get_db)):
    return crud.listar_unidades_con_estado(db)


@router.get("/{unidad_id}", response_model=schemas.UnidadEstado)
def obtener_unidad(unidad_id: int, db: Session = Depends(get_db)):
    unidad = crud.obtener_unidad(db, unidad_id)
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    return crud.calcular_estado(db, unidad)


@router.patch("/{unidad_id}/km", response_model=schemas.UnidadOut)
def actualizar_km(unidad_id: int, payload: schemas.UnidadUpdateKm, db: Session = Depends(get_db)):
    unidad = crud.actualizar_km(db, unidad_id, payload.km_actual)
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    return unidad

@router.put("/{unidad_id}", response_model=schemas.UnidadOut)
def editar_unidad(unidad_id: int, datos: schemas.UnidadUpdate, db: Session = Depends(get_db)):
    unidad = crud.actualizar_unidad(db, unidad_id, datos)
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    return unidad
