"""
Importa el CSV del informe "MANTENIMIENTO" (u otro similar) exportado desde
Samsara, y actualiza el km_actual de cada unidad usando la columna de
odómetro más confiable disponible.

No requiere token ni conexión directa a la API de Samsara: el flujo es
manual (alguien descarga el CSV del informe en Samsara y lo sube aquí),
pero automatiza la parte tediosa de capturar el km de cada unidad a mano.
"""
import csv
import io
import datetime
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..auth import requiere_modulo

router = APIRouter(prefix="/api/importar", tags=["importar"], dependencies=[Depends(requiere_modulo("importar"))])

# Posibles nombres de columna de odómetro en el CSV exportado de Samsara,
# en orden de preferencia (la primera que se encuentre y tenga dato se usa).
COLUMNAS_ODOMETRO_PREFERIDAS = [
    "Odómetro Samsara",
    "Odometro Samsara",
    "Odómetro al final",
    "Odometro al final",
]

COLUMNAS_NOMBRE_POSIBLES = ["Nombre", "Económico", "Economico"]


def _limpiar_numero(valor: str) -> float | None:
    if not valor:
        return None
    limpio = valor.replace("km", "").replace("KM", "").replace(",", "").strip()
    if not limpio:
        return None
    try:
        return float(limpio)
    except ValueError:
        return None


def _encontrar_columna(headers: list[str], candidatos: list[str]) -> str | None:
    for candidato in candidatos:
        for h in headers:
            if h.strip().lower() == candidato.strip().lower():
                return h
    return None


@router.post("/samsara-csv")
async def importar_samsara_csv(archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    contenido = await archivo.read()
    texto = contenido.decode("utf-8-sig", errors="replace")
    lector = csv.DictReader(io.StringIO(texto))

    headers = lector.fieldnames or []
    col_nombre = _encontrar_columna(headers, COLUMNAS_NOMBRE_POSIBLES)
    col_odometro = _encontrar_columna(headers, COLUMNAS_ODOMETRO_PREFERIDAS)

    if not col_nombre or not col_odometro:
        return {
            "error": "No se encontraron las columnas esperadas en el CSV.",
            "columnas_encontradas": headers,
            "se_esperaba_alguna_de_nombre": COLUMNAS_NOMBRE_POSIBLES,
            "se_esperaba_alguna_de_odometro": COLUMNAS_ODOMETRO_PREFERIDAS,
        }

    actualizadas = []
    no_encontradas = []
    sin_dato_km = []

    for fila in lector:
        nombre = (fila.get(col_nombre) or "").strip()
        if not nombre:
            continue

        km = _limpiar_numero(fila.get(col_odometro))
        if km is None:
            sin_dato_km.append(nombre)
            continue

        unidad = crud.buscar_unidad_por_nombre_samsara(db, nombre)
        if not unidad:
            no_encontradas.append(nombre)
            continue

        unidad.km_actual = km
        unidad.fecha_actualizacion_km = datetime.datetime.utcnow()
        actualizadas.append({"economico": unidad.economico, "nombre_samsara": nombre, "km_actual": km})

    db.commit()

    return {
        "actualizadas": actualizadas,
        "no_encontradas": no_encontradas,
        "sin_dato_km": sin_dato_km,
        "columna_nombre_usada": col_nombre,
        "columna_odometro_usada": col_odometro,
    }
