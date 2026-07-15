"""
Modelos de base de datos.

Tres tablas principales:

1. Unidad: cada económico de la flotilla (ej. "90"), con su kilometraje
   actual. El km_actual se puede actualizar a mano por ahora, y en el
   futuro se puede alimentar automático desde Samsara si Jorgais da acceso.

2. ReglaServicio: define cada cuántos km (o cada cuántos días) le toca
   mantenimiento preventivo a una unidad. Puede haber una regla general
   y reglas específicas por unidad.

3. Mantenimiento: el historial real de servicios hechos (preventivo o
   correctivo), con tipo, fechas de entrada/salida, costo y kilometraje
   al momento del servicio.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
import enum
import datetime

from .database import Base


class TipoMantenimiento(str, enum.Enum):
    preventivo = "preventivo"
    correctivo = "correctivo"
    otro = "otro"  # "otra reparación" - trabajos manuales que no son preventivo ni correctivo de flotilla


class SubtipoCorrectivo(str, enum.Enum):
    electrico = "electrico"
    mecanico = "mecanico"
    soldadura = "soldadura"
    otro = "otro"


class TipoUnidad(str, enum.Enum):
    propia = "propia"    # unidad de la flotilla propia, se puede actualizar via Samsara
    publico = "publico"  # vehículo de cliente externo, todo manual


class Unidad(Base):
    __tablename__ = "unidades"

    id = Column(Integer, primary_key=True, index=True)
    economico = Column(String, unique=True, index=True, nullable=False)
    descripcion = Column(String, nullable=True)
    nombre_samsara = Column(String, nullable=True)  # ej. "AVEO 012", si difiere del económico
    samsara_vehicle_id = Column(String, nullable=True)  # ID real del vehículo en Samsara (para la API)
    tipo_unidad = Column(Enum(TipoUnidad), nullable=False, default=TipoUnidad.propia)
    km_actual = Column(Float, default=0)
    fecha_actualizacion_km = Column(DateTime, default=datetime.datetime.utcnow)

    mantenimientos = relationship("Mantenimiento", back_populates="unidad")
    regla = relationship("ReglaServicio", back_populates="unidad", uselist=False)
    llantas = relationship("Llanta", back_populates="unidad")


class ReglaServicio(Base):
    __tablename__ = "reglas_servicio"

    id = Column(Integer, primary_key=True, index=True)
    unidad_id = Column(Integer, ForeignKey("unidades.id"), unique=True, nullable=False)
    intervalo_km = Column(Float, nullable=True)      # ej. 5000
    intervalo_dias = Column(Integer, nullable=True)  # ej. 180 (opcional, por tiempo)

    unidad = relationship("Unidad", back_populates="regla")


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    unidad_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)

    tipo = Column(Enum(TipoMantenimiento), nullable=False)
    subtipo_correctivo = Column(Enum(SubtipoCorrectivo), nullable=True)

    descripcion = Column(Text, nullable=True)
    km_servicio = Column(Float, nullable=False)

    fecha_entrada = Column(DateTime, nullable=False)
    fecha_salida = Column(DateTime, nullable=True)

    costo = Column(Float, default=0)

    unidad = relationship("Unidad", back_populates="mantenimientos")


class Llanta(Base):
    __tablename__ = "llantas"

    id = Column(Integer, primary_key=True, index=True)
    unidad_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)

    posicion = Column(String, nullable=False)  # ej. "delantera_izquierda", "trasera_derecha_exterior"
    marca = Column(String, nullable=True)
    modelo = Column(String, nullable=True)
    numero_serie_dot = Column(String, nullable=True)

    fecha_instalacion = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    km_instalacion = Column(Float, nullable=False, default=0)
    km_vida_util = Column(Float, nullable=True)  # ej. 80000 km de vida útil esperada

    profundidad_mm = Column(Float, nullable=True)  # última medición conocida
    fecha_ultima_inspeccion = Column(DateTime, nullable=True)

    activa = Column(Integer, default=1)  # 1 = montada actualmente, 0 = ya se cambió (histórico)

    unidad = relationship("Unidad", back_populates="llantas")
    inspecciones = relationship("InspeccionLlanta", back_populates="llanta")


class InspeccionLlanta(Base):
    __tablename__ = "inspecciones_llanta"

    id = Column(Integer, primary_key=True, index=True)
    llanta_id = Column(Integer, ForeignKey("llantas.id"), nullable=False)

    fecha = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    profundidad_mm = Column(Float, nullable=False)
    notas = Column(Text, nullable=True)

    llanta = relationship("Llanta", back_populates="inspecciones")


# ---------- Usuarios y control de accesos ----------

MODULOS_DISPONIBLES = ["unidades", "mantenimientos", "llantas", "importar"]


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nombre_completo = Column(String, nullable=True)
    es_admin = Column(Integer, default=0)  # 1 = admin, ve y edita todo, administra usuarios
    activo = Column(Integer, default=1)

    permisos = relationship("PermisoModulo", back_populates="usuario")


class PermisoModulo(Base):
    __tablename__ = "permisos_modulo"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    modulo = Column(String, nullable=False)  # uno de MODULOS_DISPONIBLES

    usuario = relationship("Usuario", back_populates="permisos")
