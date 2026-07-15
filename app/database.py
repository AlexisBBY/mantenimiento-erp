"""
Configuración de la base de datos.

Por defecto usa SQLite (archivo local, cero configuración, corre perfecto
en Mac Intel 2020). Si más adelante quieren usar PostgreSQL (por ejemplo
para desplegar en Render junto al módulo de combustible), solo cambien
la variable de entorno DATABASE_URL, por ejemplo:

    export DATABASE_URL="postgresql://usuario:password@host:5432/dbname"
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mantenimiento.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
