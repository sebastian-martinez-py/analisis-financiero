from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.database import get_db
from database.models import Deuda

router = APIRouter(prefix="/api/deudas", tags=["deudas"])


class DeudaIn(BaseModel):
    nombre:     str
    saldo:      float
    pago_min:   float
    interes:    float = 0
    estrategia: str = "bola"

class PagoIn(BaseModel):
    monto: float


@router.get("")
def list_deudas(db: Session = Depends(get_db)):
    return db.query(Deuda).all()

@router.post("", status_code=201)
def create_deuda(body: DeudaIn, db: Session = Depends(get_db)):
    d = Deuda(**body.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d

@router.post("/{deuda_id}/pago")
def registrar_pago(deuda_id: int, body: PagoIn, db: Session = Depends(get_db)):
    d = db.get(Deuda, deuda_id)
    if not d:
        raise HTTPException(404, "Deuda no encontrada")
    interes_mensual = d.saldo * (d.interes / 100 / 12)
    abono   = body.monto - interes_mensual
    d.saldo = max(0, d.saldo - abono)
    d.pagado += body.monto
    db.commit()
    db.refresh(d)
    return d

@router.delete("/{deuda_id}", status_code=204)
def delete_deuda(deuda_id: int, db: Session = Depends(get_db)):
    d = db.get(Deuda, deuda_id)
    if not d:
        raise HTTPException(404, "Deuda no encontrada")
    db.delete(d)
    db.commit()
