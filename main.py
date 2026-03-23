from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from database.database import engine
from database import models
from routers import gastos, ahorros, deudas, chat

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finanzas 50/30/20")

app.include_router(gastos.router)
app.include_router(ahorros.router)
app.include_router(deudas.router)
app.include_router(chat.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
