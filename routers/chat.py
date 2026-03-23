import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from database.database import get_db
from database.models import Gasto, Ingreso, Factura, MetaAhorro, Deuda
import anthropic

router = APIRouter(prefix="/api/chat", tags=["chat"])


def validar_usuario(usuario: str) -> str:
    usuario = usuario.strip()
    if usuario not in ["Melissa", "Sebastian"]:
        raise HTTPException(status_code=400, detail="El usuario debe ser Melissa o Sebastian")
    return usuario


class Msg(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    usuario: str
    mes: int
    anio: int
    messages: List[Msg]


def build_context(usuario: str, mes: int, anio: int, db: Session):
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
    ahorros = db.query(MetaAhorro).filter(MetaAhorro.usuario == usuario).all()
    deudas = db.query(Deuda).filter(Deuda.usuario == usuario).all()

    ingreso = ing.monto if ing else 0
    nec = sum(g.monto for g in gastos if g.cat == "Necesidades")
    des = sum(g.monto for g in gastos if g.cat == "Deseos")
    aho = sum(g.monto for g in gastos if g.cat in ("Ahorro", "Deuda"))
    sobrante = ingreso - nec - des - aho

    def pct(x):
        return f"{round(x / ingreso * 100)}%" if ingreso > 0 else "N/A"

    return f"""Eres un asesor financiero personal experto en finanzas personales y el método 50/30/20.
Respondé en español, de forma clara, útil, concreta y personalizada.
El usuario actual es {usuario}. No inventes datos.

=== DATOS DEL MES {mes}/{anio} ===
Usuario: {usuario}
Ingreso: {ingreso}
Necesidades: {nec} ({pct(nec)})
Deseos: {des} ({pct(des)})
Ahorro/Deuda: {aho} ({pct(aho)})
Sobrante: {sobrante}

Gastos: {", ".join(f"{g.desc}:{g.monto}" for g in gastos) or "ninguno"}
Facturas fijas: {", ".join(f"{f.nombre}:{f.monto}" for f in facturas) or "ninguna"}
Ahorros: {", ".join(f"{a.nombre}:{a.total_ahorrado}/{a.meta}" for a in ahorros) or "ninguno"}
Deudas: {", ".join(f"{d.nombre}:{d.saldo}" for d in deudas) or "ninguna"}
=== FIN DATOS ===

Da recomendaciones accionables.
Si ves exceso de deuda o de gasto, dilo de forma directa.
Si ves oportunidad de ahorro, indícalo.
"""


@router.post("")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or "aqui" in api_key or "sin-key" in api_key:
        raise HTTPException(status_code=400, detail="Configurá tu ANTHROPIC_API_KEY en el archivo .env")

    usuario = validar_usuario(body.usuario)

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=700,
        system=build_context(usuario, body.mes, body.anio, db),
        messages=messages,
    )

    return {"reply": response.content[0].text}
