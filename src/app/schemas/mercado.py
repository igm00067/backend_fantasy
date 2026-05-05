from pydantic import BaseModel, Field


class RealizarPujaRequest(BaseModel):
    cantidad: float = Field(gt=0)
