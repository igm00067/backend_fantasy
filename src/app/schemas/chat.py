from pydantic import BaseModel, Field
from typing import Literal, Optional


class CrearOfertaRequest(BaseModel):
    conversacion_id: int
    jugador_ofrecido_id: Optional[int] = None
    dinero_ofrecido: float = Field(default=0.0, ge=0)
    jugador_solicitado_id: Optional[int] = None
    dinero_solicitado: float = Field(default=0.0, ge=0)
    mensaje: Optional[str] = ''


class ResponderOfertaRequest(BaseModel):
    accion: Literal['ACEPTAR', 'RECHAZAR']
