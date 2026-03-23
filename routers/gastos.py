from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional
import math
from database.database import get_db
from database.models import Gasto, Ingreso, Factura, Deuda, MetaAhorro, Aporte

router = APIRouter(prefix="/api", tags=["gastos"])


def validar_usuario(usuario: str) -> str:
    usuario = usuario.strip()
    if usuario not in ["Melissa", "Sebastian"]:
        raise HTTPException(status_code=400, detail="El usuario debe ser Melissa o Sebastian")
    return usuario


class GastoIn(BaseModel):
    usuario: str
    desc: str
    monto: float
    cat: str
    subcat: str
    fecha: Optional[date] = None
    mes: int
    anio: int


class IngresoIn(BaseModel):
    usuario: str
    mes: int
    anio: int
    monto: float


class FacturaIn(BaseModel):
    usuario: str
    nombre: str
    monto: float


@router.get("/gastos")
def list_gastos(usuario: str, mes: int, anio: int, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)
    return db.query(Gasto).filter(
        Gasto.usuario == usuario,
        Gasto.mes == mes,
        Gasto.anio == anio
    ).all()


@router.post("/gastos", status_code=201)
def create_gasto(body: GastoIn, db: Session = Depends(get_db)):
    body.usuario = validar_usuario(body.usuario)
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
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(g)
    db.commit()


@router.get("/ingresos")
def get_ingreso(usuario: str, mes: int, anio: int, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)
    ing = db.query(Ingreso).filter(
        Ingreso.usuario == usuario,
        Ingreso.mes == mes,
        Ingreso.anio == anio
    ).first()
    return {"monto": ing.monto if ing else 0}


@router.put("/ingresos")
def upsert_ingreso(body: IngresoIn, db: Session = Depends(get_db)):
    body.usuario = validar_usuario(body.usuario)
    ing = db.query(Ingreso).filter(
        Ingreso.usuario == body.usuario,
        Ingreso.mes == body.mes,
        Ingreso.anio == body.anio
    ).first()
    if ing:
        ing.monto = body.monto
    else:
        ing = Ingreso(**body.model_dump())
        db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


@router.get("/facturas")
def list_facturas(usuario: str, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)
    return db.query(Factura).filter(Factura.usuario == usuario).all()


@router.post("/facturas", status_code=201)
def create_factura(body: FacturaIn, db: Session = Depends(get_db)):
    body.usuario = validar_usuario(body.usuario)
    f = Factura(**body.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.delete("/facturas/{factura_id}", status_code=204)
def delete_factura(factura_id: int, db: Session = Depends(get_db)):
    f = db.get(Factura, factura_id)
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    db.delete(f)
    db.commit()


@router.get("/resumen")
def resumen(usuario: str, mes: int, anio: int, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)

    gastos = db.query(Gasto).filter(
        Gasto.usuario == usuario,
        Gasto.mes == mes,
        Gasto.anio == anio
    ).all()

    ing = db.query(Ingreso).filter(
        Ingreso.usuario == usuario,
        Ingreso.mes == mes,
        Ingreso.anio == anio
    ).first()

    facturas = db.query(Factura).filter(Factura.usuario == usuario).all()
    deudas   = db.query(Deuda).filter(Deuda.usuario == usuario).all()
    metas    = db.query(MetaAhorro).filter(MetaAhorro.usuario == usuario).all()

    aportes_mes = db.query(Aporte).join(MetaAhorro).filter(
        MetaAhorro.usuario == usuario
    ).all()
    aportes_mes = [
        a for a in aportes_mes
        if a.fecha and a.fecha.month == mes and a.fecha.year == anio
    ]

    ingreso = ing.monto if ing else 0

    necesidades_gastos = sum(g.monto for g in gastos if g.cat == "Necesidades")
    ocio               = sum(g.monto for g in gastos if g.cat in ("Ocio", "Deseos"))
    otros_gastos       = sum(g.monto for g in gastos if g.cat not in ("Necesidades", "Ocio", "Deseos"))

    necesidades_fijas  = sum(f.monto for f in facturas)
    necesidades_totales = necesidades_gastos + necesidades_fijas

    ahorro_aportes_mes  = sum(a.monto for a in aportes_mes)
    ahorro_total_actual = sum(m.total_ahorrado for m in metas)

    deuda_total_actual  = sum(d.saldo for d in deudas)
    deuda_pagado_total  = sum(d.pagado for d in deudas)
    pago_minimo_total   = sum(d.pago_min for d in deudas)

    total_gastos_mes = necesidades_totales + ocio + otros_gastos + ahorro_aportes_mes
    sobrante         = ingreso - total_gastos_mes

    ratio_necesidades = (necesidades_totales / ingreso * 100) if ingreso > 0 else 0
    ratio_ocio        = (ocio / ingreso * 100) if ingreso > 0 else 0
    ratio_ahorro      = (ahorro_aportes_mes / ingreso * 100) if ingreso > 0 else 0
    ratio_deuda       = (deuda_total_actual / ingreso * 100) if ingreso > 0 else 0

    restante_para_distribuir = max(0, ingreso - necesidades_totales)

    # Margen libre = lo que queda despues de necesidades Y pagos minimos de deuda
    margen_libre   = max(0, restante_para_distribuir - pago_minimo_total)
    sugerido_ocio  = margen_libre * 0.6
    sugerido_ahorro = margen_libre * 0.4

    # Proyeccion de cada deuda con interes compuesto real
    proyeccion_deudas = []
    for d in deudas:
        if d.pago_min > 0 and d.saldo > 0:
            tasa_mensual = d.interes / 100 / 12
            if tasa_mensual == 0:
                meses        = d.saldo / d.pago_min
                interes_total = 0.0
            else:
                if d.pago_min <= d.saldo * tasa_mensual:
                    meses        = 9999
                    interes_total = 0.0
                else:
                    meses        = -math.log(1 - (d.saldo * tasa_mensual / d.pago_min)) / math.log(1 + tasa_mensual)
                    interes_total = (d.pago_min * meses) - d.saldo
            proyeccion_deudas.append({
                "id":              d.id,
                "nombre":          d.nombre,
                "saldo":           d.saldo,
                "pago_min":        d.pago_min,
                "interes":         d.interes,
                "estrategia":      d.estrategia,
                "pagado":          d.pagado,
                "meses_restantes": max(1, round(meses)),
                "interes_total":   round(max(0, interes_total), 2),
                "costo_total":     round(d.saldo + max(0, interes_total), 2),
            })
        else:
            proyeccion_deudas.append({
                "id":              d.id,
                "nombre":          d.nombre,
                "saldo":           d.saldo,
                "pago_min":        d.pago_min,
                "interes":         d.interes,
                "estrategia":      d.estrategia,
                "pagado":          d.pagado,
                "meses_restantes": round(d.saldo / d.pago_min) if d.pago_min > 0 else 0,
                "interes_total":   0.0,
                "costo_total":     d.saldo,
            })

    return {
        "usuario":                usuario,
        "ingreso":                ingreso,
        "necesidades_gastos":     necesidades_gastos,
        "necesidades_fijas":      necesidades_fijas,
        "necesidades_totales":    necesidades_totales,
        "ocio":                   ocio,
        "deseos":                 ocio,         # compatibilidad
        "otros_gastos":           otros_gastos,
        "ahorro_aportes_mes":     ahorro_aportes_mes,
        "ahorro_total_actual":    ahorro_total_actual,
        "deuda_total_actual":     deuda_total_actual,
        "deuda_pagado_total":     deuda_pagado_total,
        "pago_minimo_total":      round(pago_minimo_total, 2),
        "sobrante":               sobrante,
        "total_gastos":           total_gastos_mes,
        "ratio_necesidades":      round(ratio_necesidades, 2),
        "ratio_ocio":             round(ratio_ocio, 2),
        "ratio_deseos":           round(ratio_ocio, 2),  # compatibilidad
        "ratio_ahorro":           round(ratio_ahorro, 2),
        "ratio_deuda":            round(ratio_deuda, 2),
        "restante_para_distribuir": round(restante_para_distribuir, 2),
        "margen_libre":           round(margen_libre, 2),
        "sugerido_ocio":          round(sugerido_ocio, 2),
        "sugerido_deseos":        round(sugerido_ocio, 2),  # compatibilidad
        "sugerido_ahorro":        round(sugerido_ahorro, 2),
        "gastos":                 gastos,
        "facturas":               facturas,
        "deudas":                 proyeccion_deudas,
        "metas":                  metas,
    }


@router.get("/historico")
def historico(usuario: str, anio: int, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)
    resultado = []

    facturas = db.query(Factura).filter(Factura.usuario == usuario).all()
    necesidades_fijas = sum(f.monto for f in facturas)

    for mes in range(1, 13):
        gastos = db.query(Gasto).filter(
            Gasto.usuario == usuario,
            Gasto.mes == mes,
            Gasto.anio == anio
        ).all()

        ing = db.query(Ingreso).filter(
            Ingreso.usuario == usuario,
            Ingreso.mes == mes,
            Ingreso.anio == anio
        ).first()

        aportes_mes = db.query(Aporte).join(MetaAhorro).filter(
            MetaAhorro.usuario == usuario
        ).all()
        aportes_mes = [
            a for a in aportes_mes
            if a.fecha and a.fecha.month == mes and a.fecha.year == anio
        ]

        ingreso = ing.monto if ing else 0
        necesidades_gastos = sum(g.monto for g in gastos if g.cat == "Necesidades")
        ocio = sum(g.monto for g in gastos if g.cat in ("Ocio", "Deseos"))
        otros_gastos = sum(g.monto for g in gastos if g.cat not in ("Necesidades", "Ocio", "Deseos"))
        ahorro_mes = sum(a.monto for a in aportes_mes)

        necesidades_totales = necesidades_gastos + necesidades_fijas
        total_gastos = necesidades_totales + ocio + otros_gastos + ahorro_mes

        resultado.append({
            "usuario":      usuario,
            "mes":          mes,
            "anio":         anio,
            "ingreso":      ingreso,
            "necesidades":  necesidades_totales,
            "deseos":       ocio,
            "ahorro_deuda": ahorro_mes + otros_gastos,
            "total_gastos": total_gastos,
            "sobrante":     ingreso - total_gastos,
        })

    return resultado
