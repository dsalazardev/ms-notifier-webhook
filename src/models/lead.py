from pydantic import BaseModel, EmailStr, Field


class LeadCreate(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico del prospecto")
    need: str = Field(..., description="Necesidad o requerimiento del prospecto")
