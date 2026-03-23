from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional
from database.database import get_db
from database.models import Gasto, Ingreso, Factura

router = APIRouter(prefix="/api", tags=["gastos"])


class GastoIn(BaseModel):
    desc:   str
    monto:  float
    cat:    str
    subcat: str
    fecha:  Optional[date] = None
    mes:    int
    anio:   int

class IngresoIn(BaseModel):
    mes:   int
    anio:  int
    monto: float

class FacturaIn(BaseModel):
    nombre: str
    monto:  float


@router.get("/gastos")
def list_gastos(mes: int, anio: int, db: Session = Depends(get_db)):
    return db.query(Gasto).filter(Gasto.mes == mes, Gasto.anio == anio).all()

@router.post("/gastos", status_code=201)
def create_gasto(body: GastoIn, db: Session = Depends(get_db)):
    g = Gasto(**body.model_dump())
    if g.fecha is None:
        g.fecha = date.today()
    db.add(g)
    db.commit()
    db.refresh(g)
    return g

@router.delete("/gastos/{gasto_id}", status_code=204)
def delete_gasto(gasto_id: int, db: Session = Depends(get_db)):
    g = db.get(Gasto, gasto_id)
    if not g:
        raise HTTPException(404, "Gasto no encontrado")
    db.delete(g)
    db.commit()


@router.get("/ingresos")
def get_ingreso(mes: int, anio: int, db: Session = Depends(get_db)):
    ing = db.query(Ingreso).filter(Ingreso.mes == mes, Ingreso.anio == anio).first()
    return {"monto": ing.monto if ing else 0}

@router.put("/ingresos")
def upsert_ingreso(body: IngresoIn, db: Session = Depends(get_db)):
    ing = db.query(Ingreso).filter(Ingreso.mes == body.mes, Ingreso.anio == body.anio).first()
    if ing:
        ing.monto = body.monto
    else:
        ing = Ingreso(**body.model_dump())
        db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


@router.get("/facturas")
def list_facturas(db: Session = Depends(get_db)):
    return db.query(Factura).all()

@router.post("/facturas", status_code=201)
def create_factura(body: FacturaIn, db: Session = Depends(get_db)):
    f = Factura(**body.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    return f

@router.delete("/facturas/{factura_id}", status_code=204)
def delete_factura(factura_id: int, db: Session = Depends(get_db)):
    f = db.get(Factura, factura_id)
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    db.delete(f)
    db.commit()


@router.get("/resumen")
def resumen(mes: int, anio: int, db: Session = Depends(get_db)):
    gastos  = db.query(Gasto).filter(Gasto.mes == mes, Gasto.anio == anio).all()
    ing     = db.query(Ingreso).filter(Ingreso.mes == mes, Ingreso.anio == anio).first()
    ingreso = ing.monto if ing else 0
    nec = sum(g.monto for g in gastos if g.cat == "Necesidades")
    des = sum(g.monto for g in gastos if g.cat == "Deseos")
    aho = sum(g.monto for g in gastos if g.cat in ("Ahorro", "Deuda"))
    return {
        "ingreso": ingreso, "necesidades": nec, "deseos": des,
        "ahorro_deuda": aho, "sobrante": ingreso - nec - des - aho,
        "gastos": gastos,
    }


@router.get("/historico")
def historico(anio: int, db: Session = Depends(get_db)):
    resultado = []
    for mes in range(1, 13):
        gastos  = db.query(Gasto).filter(Gasto.mes == mes, Gasto.anio == anio).all()
        ing     = db.query(Ingreso).filter(Ingreso.mes == mes, Ingreso.anio == anio).first()
        ingreso = ing.monto if ing else 0
        nec = sum(g.monto for g in gastos if g.cat == "Necesidades")
        des = sum(g.monto for g in gastos if g.cat == "Deseos")
        aho = sum(g.monto for g in gastos if g.cat in ("Ahorro", "Deuda"))
        resultado.append({
            "mes": mes, "anio": anio, "ingreso": ingreso,
            "necesidades": nec, "deseos": des, "ahorro_deuda": aho,
            "total_gastos": nec + des + aho,
        })
    return resultado
