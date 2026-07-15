"""
Funciones de acceso a datos y la lógica de negocio central:
calcular cuándo le toca servicio a cada unidad.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
import datetime

from . import models, schemas


# ---------- Unidades ----------

def crear_unidad(db: Session, unidad: schemas.UnidadCreate) -> models.Unidad:
    db_unidad = models.Unidad(
        economico=unidad.economico,
        descripcion=unidad.descripcion,
        nombre_samsara=unidad.nombre_samsara,
        samsara_vehicle_id=unidad.samsara_vehicle_id,   # <-- ESTA LÍNEA ES LA NUEVA, agrégala aquí
        tipo_unidad=unidad.tipo_unidad,
        km_actual=unidad.km_actual,
        fecha_actualizacion_km=datetime.datetime.utcnow(),
    )
    db.add(db_unidad)
    db.commit()
    db.refresh(db_unidad)

    if unidad.intervalo_km or unidad.intervalo_dias:
        regla = models.ReglaServicio(
            unidad_id=db_unidad.id,
            intervalo_km=unidad.intervalo_km,
            intervalo_dias=unidad.intervalo_dias,
        )
        db.add(regla)
        db.commit()
        db.refresh(db_unidad)

    return db_unidad
def listar_unidades(db: Session):
    return db.query(models.Unidad).all()


def obtener_unidad(db: Session, unidad_id: int):
    return db.query(models.Unidad).filter(models.Unidad.id == unidad_id).first()


def buscar_unidad_por_nombre_samsara(db: Session, nombre: str):
    """
    Busca una unidad que coincida con el nombre que trae el informe de Samsara.
    Primero intenta por el campo nombre_samsara (mapeo explícito), y si no
    hay match, prueba directo contra el económico (por si coinciden).
    Comparación insensible a mayúsculas/espacios.
    """
    nombre_normalizado = nombre.strip().lower()

    unidades = db.query(models.Unidad).all()
    for u in unidades:
        if u.nombre_samsara and u.nombre_samsara.strip().lower() == nombre_normalizado:
            return u
    for u in unidades:
        if u.economico.strip().lower() == nombre_normalizado:
            return u
    return None


def actualizar_km(db: Session, unidad_id: int, km_actual: float):
    unidad = obtener_unidad(db, unidad_id)
    if not unidad:
        return None
    unidad.km_actual = km_actual
    unidad.fecha_actualizacion_km = datetime.datetime.utcnow()
    db.commit()
    db.refresh(unidad)
    return unidad

def actualizar_unidad(db: Session, unidad_id: int, datos: schemas.UnidadUpdate):
    unidad = obtener_unidad(db, unidad_id)
    if not unidad:
        return None

    if datos.economico is not None:
        unidad.economico = datos.economico
    if datos.descripcion is not None:
        unidad.descripcion = datos.descripcion
    if datos.nombre_samsara is not None:
        unidad.nombre_samsara = datos.nombre_samsara
    if datos.samsara_vehicle_id is not None:            # <-- NUEVA
        unidad.samsara_vehicle_id = datos.samsara_vehicle_id   # <-- NUEVA
    if datos.tipo_unidad is not None:
        unidad.tipo_unidad = datos.tipo_unidad

    if datos.intervalo_km is not None or datos.intervalo_dias is not None:
        if unidad.regla:
            if datos.intervalo_km is not None:
                unidad.regla.intervalo_km = datos.intervalo_km
            if datos.intervalo_dias is not None:
                unidad.regla.intervalo_dias = datos.intervalo_dias
        else:
            nueva_regla = models.ReglaServicio(
                unidad_id=unidad.id,
                intervalo_km=datos.intervalo_km,
                intervalo_dias=datos.intervalo_dias,
            )
            db.add(nueva_regla)

    db.commit()
    db.refresh(unidad)
    return unidad
# ---------- Mantenimientos ----------

def crear_mantenimiento(db: Session, mant: schemas.MantenimientoCreate) -> models.Mantenimiento:
    db_mant = models.Mantenimiento(**mant.model_dump())
    db.add(db_mant)
    db.commit()
    db.refresh(db_mant)
    return db_mant


def listar_mantenimientos(db: Session, unidad_id: int | None = None):
    q = db.query(models.Mantenimiento)
    if unidad_id is not None:
        q = q.filter(models.Mantenimiento.unidad_id == unidad_id)
    return q.order_by(desc(models.Mantenimiento.fecha_entrada)).all()


def ultimo_preventivo(db: Session, unidad_id: int):
    return (
        db.query(models.Mantenimiento)
        .filter(
            models.Mantenimiento.unidad_id == unidad_id,
            models.Mantenimiento.tipo == models.TipoMantenimiento.preventivo,
        )
        .order_by(desc(models.Mantenimiento.km_servicio))
        .first()
    )


# ---------- Cálculo de estado de servicio ----------

UMBRAL_PROXIMO_KM = 500  # a cuántos km antes del límite se marca "próximo"


def calcular_estado(db: Session, unidad: models.Unidad) -> schemas.UnidadEstado:
    """
    Regla: próximo_km_servicio = km del último preventivo + intervalo_km.
    Si no hay preventivo previo, se toma como base 0 (o se puede ajustar
    a mano capturando un mantenimiento inicial "de referencia").
    """
    datos = schemas.UnidadOut.model_validate(unidad, from_attributes=True).model_dump()

    if not unidad.regla or not unidad.regla.intervalo_km:
        return schemas.UnidadEstado(**datos, estado="sin_regla")

    ultimo = ultimo_preventivo(db, unidad.id)
    km_base = ultimo.km_servicio if ultimo else 0
    proximo = km_base + unidad.regla.intervalo_km

    restantes = proximo - unidad.km_actual

    if restantes < 0:
        estado = "vencido"
    elif restantes <= UMBRAL_PROXIMO_KM:
        estado = "proximo"
    else:
        estado = "al_corriente"

    return schemas.UnidadEstado(
        **datos, proximo_km_servicio=proximo, km_restantes=restantes, estado=estado
    )


def listar_unidades_con_estado(db: Session):
    unidades = listar_unidades(db)
    return [calcular_estado(db, u) for u in unidades]


# ---------- Llantas ----------

UMBRAL_PROXIMO_KM_LLANTA = 5000       # a cuántos km antes del límite de vida útil se marca "próximo"
PROFUNDIDAD_MINIMA_MM = 3.0           # por debajo de esto, se considera vencida (criterio típico de reemplazo)
PROFUNDIDAD_ALERTA_MM = 5.0           # por debajo de esto (pero arriba del mínimo), se marca "próximo"


def crear_llanta(db: Session, llanta: schemas.LlantaCreate) -> models.Llanta:
    db_llanta = models.Llanta(**llanta.model_dump())
    db.add(db_llanta)
    db.commit()
    db.refresh(db_llanta)
    return db_llanta


def listar_llantas(db: Session, unidad_id: int | None = None, solo_activas: bool = True):
    q = db.query(models.Llanta)
    if unidad_id is not None:
        q = q.filter(models.Llanta.unidad_id == unidad_id)
    if solo_activas:
        q = q.filter(models.Llanta.activa == 1)
    return q.all()


def obtener_llanta(db: Session, llanta_id: int):
    return db.query(models.Llanta).filter(models.Llanta.id == llanta_id).first()


def dar_de_baja_llanta(db: Session, llanta_id: int):
    """Marca la llanta como ya no montada (se cambió). Queda en el histórico."""
    llanta = obtener_llanta(db, llanta_id)
    if not llanta:
        return None
    llanta.activa = 0
    db.commit()
    db.refresh(llanta)
    return llanta


def registrar_inspeccion_llanta(db: Session, llanta_id: int, inspeccion: schemas.InspeccionLlantaCreate):
    llanta = obtener_llanta(db, llanta_id)
    if not llanta:
        return None

    fecha = inspeccion.fecha or datetime.datetime.utcnow()
    db_insp = models.InspeccionLlanta(
        llanta_id=llanta_id,
        fecha=fecha,
        profundidad_mm=inspeccion.profundidad_mm,
        notas=inspeccion.notas,
    )
    db.add(db_insp)

    # Actualiza el "último dato conocido" en la llanta misma
    llanta.profundidad_mm = inspeccion.profundidad_mm
    llanta.fecha_ultima_inspeccion = fecha

    db.commit()
    db.refresh(db_insp)
    return db_insp


def listar_inspecciones_llanta(db: Session, llanta_id: int):
    return (
        db.query(models.InspeccionLlanta)
        .filter(models.InspeccionLlanta.llanta_id == llanta_id)
        .order_by(desc(models.InspeccionLlanta.fecha))
        .all()
    )


def calcular_estado_llanta(db: Session, llanta: models.Llanta) -> schemas.LlantaEstado:
    """
    Una llanta se marca "vencida" si se pasó del km de vida útil O si su
    profundidad de dibujo ya está en el mínimo de reemplazo (lo que ocurra
    primero). Si falta algún dato para evaluar, se marca "sin_dato".
    """
    datos = schemas.LlantaOut.model_validate(llanta, from_attributes=True).model_dump()
    unidad = llanta.unidad

    km_recorridos = None
    km_restantes = None
    estado_km = None

    if llanta.km_vida_util and unidad:
        km_recorridos = unidad.km_actual - llanta.km_instalacion
        km_restantes = llanta.km_vida_util - km_recorridos
        if km_restantes < 0:
            estado_km = "vencido"
        elif km_restantes <= UMBRAL_PROXIMO_KM_LLANTA:
            estado_km = "proximo"
        else:
            estado_km = "al_corriente"

    estado_profundidad = None
    if llanta.profundidad_mm is not None:
        if llanta.profundidad_mm <= PROFUNDIDAD_MINIMA_MM:
            estado_profundidad = "vencido"
        elif llanta.profundidad_mm <= PROFUNDIDAD_ALERTA_MM:
            estado_profundidad = "proximo"
        else:
            estado_profundidad = "al_corriente"

    # El peor de los dos estados manda (vencido > proximo > al_corriente)
    prioridad = {"vencido": 3, "proximo": 2, "al_corriente": 1, None: 0}
    estado_final = max([estado_km, estado_profundidad], key=lambda e: prioridad[e])
    if estado_final is None:
        estado_final = "sin_dato"

    veces_renovada = (
        db.query(models.Llanta)
        .filter(
            models.Llanta.unidad_id == llanta.unidad_id,
            models.Llanta.posicion == llanta.posicion,
            models.Llanta.activa == 0,
        )
        .count()
    )

    return schemas.LlantaEstado(
        **datos,
        km_recorridos=km_recorridos,
        km_restantes_vida_util=km_restantes,
        veces_renovada=veces_renovada,
        estado=estado_final,
    )


def listar_llantas_con_estado(db: Session, unidad_id: int | None = None):
    llantas = listar_llantas(db, unidad_id=unidad_id)
    return [calcular_estado_llanta(db, l) for l in llantas]


# ---------- Alertas (agregador) ----------

def obtener_alertas(db: Session):
    """
    Junta en un solo lugar todas las unidades y llantas en estado
    'proximo' o 'vencido', para poder mostrarlas de forma destacada
    (ej. una sección de "Alertas activas" en el dashboard).
    """
    unidades = listar_unidades_con_estado(db)
    llantas = listar_llantas_con_estado(db)

    unidades_alerta = [u for u in unidades if u.estado in ("proximo", "vencido")]
    llantas_alerta = [l for l in llantas if l.estado in ("proximo", "vencido")]

    return {
        "unidades": unidades_alerta,
        "llantas": llantas_alerta,
        "total": len(unidades_alerta) + len(llantas_alerta),
    }


# ---------- Usuarios y permisos ----------

def usuario_a_schema(usuario: models.Usuario) -> schemas.UsuarioOut:
    return schemas.UsuarioOut(
        id=usuario.id,
        username=usuario.username,
        nombre_completo=usuario.nombre_completo,
        es_admin=bool(usuario.es_admin),
        activo=bool(usuario.activo),
        modulos_permitidos=[p.modulo for p in usuario.permisos],
    )


def listar_usuarios(db: Session):
    return db.query(models.Usuario).all()


def obtener_usuario_por_username(db: Session, username: str):
    return db.query(models.Usuario).filter(models.Usuario.username == username).first()


def crear_usuario(db: Session, datos: schemas.UsuarioCreate) -> models.Usuario:
    from .auth import hash_password

    db_usuario = models.Usuario(
        username=datos.username,
        password_hash=hash_password(datos.password),
        nombre_completo=datos.nombre_completo,
        es_admin=1 if datos.es_admin else 0,
        activo=1,
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)

    for modulo in datos.modulos_permitidos:
        if modulo in models.MODULOS_DISPONIBLES:
            db.add(models.PermisoModulo(usuario_id=db_usuario.id, modulo=modulo))
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def actualizar_permisos(db: Session, usuario_id: int, modulos: list[str]):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        return None

    db.query(models.PermisoModulo).filter(models.PermisoModulo.usuario_id == usuario_id).delete()
    for modulo in modulos:
        if modulo in models.MODULOS_DISPONIBLES:
            db.add(models.PermisoModulo(usuario_id=usuario_id, modulo=modulo))
    db.commit()
    db.refresh(usuario)
    return usuario


def desactivar_usuario(db: Session, usuario_id: int):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        return None
    usuario.activo = 0
    db.commit()
    db.refresh(usuario)
    return usuario
def unidades_con_mapeo_samsara(db: Session):
    return db.query(models.Unidad).filter(models.Unidad.samsara_vehicle_id.isnot(None)).all()


def sincronizar_km_con_samsara(db: Session, odometros_por_vehicle_id: dict):
    actualizadas = []
    sin_dato = []
    for unidad in unidades_con_mapeo_samsara(db):
        km = odometros_por_vehicle_id.get(unidad.samsara_vehicle_id)
        if km is None:
            sin_dato.append(unidad.economico)
            continue
        unidad.km_actual = km
        unidad.fecha_actualizacion_km = datetime.datetime.utcnow()
        actualizadas.append({"economico": unidad.economico, "samsara_vehicle_id": unidad.samsara_vehicle_id, "km_actual": km})
    db.commit()
    return {"actualizadas": actualizadas, "sin_dato": sin_dato}