from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, schemas
from ..database import get_db
from ..auth import requiere_modulo

router = APIRouter(prefix="/api/llantas", tags=["llantas"], dependencies=[Depends(requiere_modulo("llantas"))])


@router.post("/", response_model=schemas.LlantaOut)
def crear_llanta(llanta: schemas.LlantaCreate, db: Session = Depends(get_db)):
    unidad = crud.obtener_unidad(db, llanta.unidad_id)
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    return crud.crear_llanta(db, llanta)


@router.get("/", response_model=List[schemas.LlantaEstado])
def listar_llantas(unidad_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.listar_llantas_con_estado(db, unidad_id)


@router.post("/{llanta_id}/dar-de-baja", response_model=schemas.LlantaOut)
def dar_de_baja(llanta_id: int, db: Session = Depends(get_db)):
    llanta = crud.dar_de_baja_llanta(db, llanta_id)
    if not llanta:
        raise HTTPException(status_code=404, detail="Llanta no encontrada")
    return llanta


@router.post("/{llanta_id}/inspecciones", response_model=schemas.InspeccionLlantaOut)
def registrar_inspeccion(llanta_id: int, inspeccion: schemas.InspeccionLlantaCreate, db: Session = Depends(get_db)):
    resultado = crud.registrar_inspeccion_llanta(db, llanta_id, inspeccion)
    if not resultado:
        raise HTTPException(status_code=404, detail="Llanta no encontrada")
    return resultado


@router.get("/{llanta_id}/inspecciones", response_model=List[schemas.InspeccionLlantaOut])
def listar_inspecciones(llanta_id: int, db: Session = Depends(get_db)):
    return crud.listar_inspecciones_llanta(db, llanta_id)
