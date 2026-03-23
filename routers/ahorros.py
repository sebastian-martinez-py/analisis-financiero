from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from database.database import get_db
from database.models import MetaAhorro, Aporte

router = APIRouter(prefix="/api/ahorros", tags=["ahorros"])


def validar_usuario(usuario: str) -> str:
    usuario = usuario.strip()
    if usuario not in ["Melissa", "Sebastian"]:
        raise HTTPException(status_code=400, detail="El usuario debe ser Melissa o Sebastian")
    return usuario


class MetaIn(BaseModel):
    usuario: str
    nombre: str
    meta: float
    inicial: float = 0
    mensual: float = 0


class AporteIn(BaseModel):
    meta_id: int
    monto: float
    nota: str = ""


@router.get("")
def list_metas(usuario: str, db: Session = Depends(get_db)):
    usuario = validar_usuario(usuario)
    return db.query(MetaAhorro).filter(MetaAhorro.usuario == usuario).all()


@router.post("", status_code=201)
def create_meta(body: MetaIn, db: Session = Depends(get_db)):
    body.usuario = validar_usuario(body.usuario)
    m = MetaAhorro(**body.model_dump(), total_ahorrado=body.inicial)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{meta_id}", status_code=204)
def delete_meta(meta_id: int, db: Session = Depends(get_db)):
    m = db.get(MetaAhorro, meta_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    db.delete(m)
    db.commit()


@router.post("/aportes", status_code=201)
def registrar_aporte(body: AporteIn, db: Session = Depends(get_db)):
    meta = db.get(MetaAhorro, body.meta_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Meta no encontrada")

    aporte = Aporte(
        meta_id=body.meta_id,
        monto=body.monto,
        nota=body.nota,
        fecha=date.today()
    )
    meta.total_ahorrado += body.monto

    db.add(aporte)
    db.commit()
    db.refresh(aporte)
    return aporte
