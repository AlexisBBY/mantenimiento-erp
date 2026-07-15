"""
Schemas de Pydantic: definen qué datos entran y salen de cada endpoint.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime

from .models import TipoMantenimiento, SubtipoCorrectivo, TipoUnidad


# ---------- Unidad ----------

class UnidadBase(BaseModel):
    economico: str
    descripcion: Optional[str] = None
    nombre_samsara: Optional[str] = None
    tipo_unidad: TipoUnidad = TipoUnidad.propia


class UnidadCreate(UnidadBase):
    km_actual: float = 0
    intervalo_km: Optional[float] = None
    intervalo_dias: Optional[int] = None

class UnidadUpdate(BaseModel):
    economico: Optional[str] = None
    descripcion: Optional[str] = None
    nombre_samsara: Optional[str] = None
    tipo_unidad: Optional[TipoUnidad] = None
    intervalo_km: Optional[float] = None
    intervalo_dias: Optional[int] = None


class UnidadUpdateKm(BaseModel):
    km_actual: float


class ReglaServicioOut(BaseModel):
    intervalo_km: Optional[float] = None
    intervalo_dias: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UnidadOut(UnidadBase):
    id: int
    km_actual: float
    fecha_actualizacion_km: datetime.datetime
    regla: Optional[ReglaServicioOut] = None

    model_config = ConfigDict(from_attributes=True)


class UnidadEstado(UnidadOut):
    """Unidad + cálculo de estado de servicio (al_corriente/proximo/vencido)."""
    proximo_km_servicio: Optional[float] = None
    km_restantes: Optional[float] = None
    estado: str  # "al_corriente" | "proximo" | "vencido" | "sin_regla"


# ---------- Mantenimiento ----------

class MantenimientoBase(BaseModel):
    tipo: TipoMantenimiento
    subtipo_correctivo: Optional[SubtipoCorrectivo] = None
    descripcion: Optional[str] = None
    km_servicio: float
    fecha_entrada: datetime.datetime
    fecha_salida: Optional[datetime.datetime] = None
    costo: float = 0


class MantenimientoCreate(MantenimientoBase):
    unidad_id: int


class MantenimientoOut(MantenimientoBase):
    id: int
    unidad_id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Llantas ----------

class LlantaBase(BaseModel):
    posicion: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie_dot: Optional[str] = None
    fecha_instalacion: datetime.datetime
    km_instalacion: float = 0
    km_vida_util: Optional[float] = None
    profundidad_mm: Optional[float] = None


class LlantaCreate(LlantaBase):
    unidad_id: int


class LlantaOut(LlantaBase):
    id: int
    unidad_id: int
    fecha_ultima_inspeccion: Optional[datetime.datetime] = None
    activa: int

    model_config = ConfigDict(from_attributes=True)


class LlantaEstado(LlantaOut):
    """Llanta + cálculo de estado (por km de vida útil y por profundidad)."""
    km_recorridos: Optional[float] = None
    km_restantes_vida_util: Optional[float] = None
    veces_renovada: int = 0  # cuántas llantas anteriores hubo en esta misma posición
    estado: str  # "al_corriente" | "proximo" | "vencido" | "sin_dato"


class InspeccionLlantaCreate(BaseModel):
    profundidad_mm: float
    notas: Optional[str] = None
    fecha: Optional[datetime.datetime] = None


class InspeccionLlantaOut(BaseModel):
    id: int
    llanta_id: int
    fecha: datetime.datetime
    profundidad_mm: float
    notas: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Autenticación y usuarios ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class UsuarioOut(BaseModel):
    id: int
    username: str
    nombre_completo: Optional[str] = None
    es_admin: bool
    activo: bool
    modulos_permitidos: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(BaseModel):
    username: str
    password: str
    nombre_completo: Optional[str] = None
    es_admin: bool = False
    modulos_permitidos: list[str] = []


class PermisosUpdate(BaseModel):
    modulos_permitidos: list[str]


class CambiarPassword(BaseModel):
    password_actual: str
    password_nueva: str
