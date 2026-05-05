from pydantic import BaseModel, Field
from typing import List, Optional


class TitularSchema(BaseModel):
    jugador_id: int
    posicion_en_campo: str


class CrearLigaRequest(BaseModel):
    nombre: str
    competicion_id: int
    nombre_equipo: Optional[str] = 'Mi Equipo'
    max_participantes: int = Field(default=10, ge=2, le=20)
    presupuesto_inicial: float = Field(default=100.0, ge=0)
    max_jugadores_por_equipo: int = Field(default=24, ge=11, le=30)


class UnirseALigaRequest(BaseModel):
    codigo_invitacion: str
    nombre_equipo: Optional[str] = 'Mi Equipo'


class GuardarAlineacionRequest(BaseModel):
    formacion: str = '4-3-3'
    titulares: List[TitularSchema]


class VenderJugadorRequest(BaseModel):
    jugador_id: int
