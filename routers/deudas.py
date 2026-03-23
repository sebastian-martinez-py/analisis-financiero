from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.database import get_db
from database.models import Deuda

router = APIRouter(prefix="/api/deudas", tags=["deudas"])


def validar_usuario(usuario: str) -> str:
    usuario = usuario.strip()
    if usuario not in ["Melissa", "Sebastian"]:
        raise HTTPException(status_code=400, detail="El usuario debe ser Melissa o Sebastian")
    return usuario


class DeudaIn(BaseModel):
    usuario: str
    nombre: str
    saldo: float
    pago_min: float
    interes: float = 0
    estrategia: str = "bola"


class PagoIn(BaseModel):
    monto: float


@router.get("")
def list_deudas(usuario: str, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)
    return db.query(Deuda).filter(Deuda.usuario == usuario).all()


@router.post("", status_code=201)
def create_deuda(body: DeudaIn, db: Session = Depends(get_db)):
    body.usuario = validar_usuario(body.usuario)
    deuda = Deuda(**body.model_dump())
    db.add(deuda)
    db.commit()
    db.refresh(deuda)
    return deuda


@router.delete("/{deuda_id}", status_code=204)
def delete_deuda(deuda_id: int, db: Session = Depends(get_db)):
    deuda = db.get(Deuda, deuda_id)
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    db.delete(deuda)
    db.commit()


@router.post("/{deuda_id}/pagar")
def pagar_deuda(deuda_id: int, body: PagoIn, db: Session = Depends(get_db)):
    deuda = db.get(Deuda, deuda_id)
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")

    deuda.pagado += body.monto
    deuda.saldo = max(0, deuda.saldo - body.monto)

    db.commit()
    db.refresh(deuda)
    return deuda
