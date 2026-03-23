from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import os
import anthropic
from database.database import get_db
from database.models import Gasto, Ingreso, MetaAhorro, Deuda, Factura

router = APIRouter(prefix="/api/chat", tags=["chat"])


class Mensaje(BaseModel):
    role:    str
    content: str

class ChatIn(BaseModel):
    messages: List[Mensaje]
    mes:      int
    anio:     int


def build_context(mes: int, anio: int, db: Session) -> str:
    gastos   = db.query(Gasto).filter(Gasto.mes == mes, Gasto.anio == anio).all()
    ing      = db.query(Ingreso).filter(Ingreso.mes == mes, Ingreso.anio == anio).first()
    ahorros  = db.query(MetaAhorro).all()
    deudas   = db.query(Deuda).all()
    facturas = db.query(Factura).all()

    ingreso = ing.monto if ing else 0
    nec = sum(g.monto for g in gastos if g.cat == "Necesidades")
    des = sum(g.monto for g in gastos if g.cat == "Deseos")
    aho = sum(g.monto for g in gastos if g.cat in ("Ahorro", "Deuda"))
    pct = lambda x: f"{round(x/ingreso*100)}%" if ingreso > 0 else "N/A"

    return f"""Eres un asesor financiero personal experto en el método 50/30/20.
Tenés acceso a los datos reales del usuario. Respondé en español, de forma concisa y con consejos accionables.

=== DATOS DEL MES {mes}/{anio} ===
Ingreso: {ingreso}
Necesidades: {nec} ({pct(nec)} — meta 50%)
Deseos: {des} ({pct(des)} — meta 30%)
Ahorro/Deuda: {aho} ({pct(aho)} — meta 20%)
Sobrante: {ingreso - nec - des - aho}

Gastos: {", ".join(f"{g.desc}:{g.monto}" for g in gastos) or "ninguno"}
Facturas fijas: {", ".join(f"{f.nombre}:{f.monto}" for f in facturas) or "ninguna"}
Ahorros: {", ".join(f"{a.nombre}:{a.total_ahorrado}/{a.meta}" for a in ahorros) or "ninguno"}
Deudas: {", ".join(f"{d.nombre}:{d.saldo}" for d in deudas) or "ninguna"}
=== FIN DATOS ==="""


@router.post("")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or "aqui" in api_key or "sin-key" in api_key:
        raise HTTPException(400, "Configurá tu ANTHROPIC_API_KEY en el archivo .env")

    client   = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=build_context(body.mes, body.anio, db),
        messages=messages,
    )
    return {"reply": response.content[0].text}
