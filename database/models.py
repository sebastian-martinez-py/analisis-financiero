from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, default=1)
    moneda = Column(String, default="₡")


class Ingreso(Base):
    __tablename__ = "ingresos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String, nullable=False, default="Sebastian")
    mes = Column(Integer, nullable=False)
    anio = Column(Integer, nullable=False)
    monto = Column(Float, nullable=False, default=0)


class Gasto(Base):
    __tablename__ = "gastos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String, nullable=False, default="Sebastian")
    desc = Column(String, nullable=False)
    monto = Column(Float, nullable=False)
    cat = Column(String, nullable=False)
    subcat = Column(String, nullable=False)
    fecha = Column(Date, default=date.today)
    mes = Column(Integer, nullable=False)
    anio = Column(Integer, nullable=False)


class Factura(Base):
    __tablename__ = "facturas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String, nullable=False, default="Sebastian")
    nombre = Column(String, nullable=False)
    monto = Column(Float, nullable=False)


class MetaAhorro(Base):
    __tablename__ = "metas_ahorro"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String, nullable=False, default="Sebastian")
    nombre = Column(String, nullable=False)
    meta = Column(Float, nullable=False)
    inicial = Column(Float, default=0)
    mensual = Column(Float, default=0)
    total_ahorrado = Column(Float, default=0)
    aportes = relationship("Aporte", back_populates="meta_obj", cascade="all, delete")


class Aporte(Base):
    __tablename__ = "aportes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    meta_id = Column(Integer, ForeignKey("metas_ahorro.id"), nullable=False)
    monto = Column(Float, nullable=False)
    nota = Column(String, default="")
    fecha = Column(Date, default=date.today)
    meta_obj = relationship("MetaAhorro", back_populates="aportes")


class Deuda(Base):
    __tablename__ = "deudas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String, nullable=False, default="Sebastian")
    nombre = Column(String, nullable=False)
    saldo = Column(Float, nullable=False)
    pagado = Column(Float, default=0)
    pago_min = Column(Float, nullable=False)
    interes = Column(Float, default=0)
    estrategia = Column(String, default="bola")
