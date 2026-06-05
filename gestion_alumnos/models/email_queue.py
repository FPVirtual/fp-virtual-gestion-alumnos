"""Modelo para la cola de emails pendientes.

Cada instancia representa un email que debe enviarse,
con su plantilla, datos y estado de envío.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator


class EmailJob(BaseModel):
    """Trabajo de email pendiente de envío.

    Se serializa como fila en un CSV para permitir
    procesamiento externo y recuperación ante fallos.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_name: str = Field(description="Nombre del template HTML a usar")
    recipient: str = Field(description="Email del destinatario")
    subject: str = Field(description="Asunto del email")
    template_data: dict = Field(
        default_factory=dict,
        description="Datos para renderizar el template",
    )
    status: Literal["pending", "sent", "failed"] = Field(default="pending")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    sent_at: str | None = Field(default=None)
    error: str | None = Field(default=None)

    @field_validator("template_data", mode="before")
    @classmethod
    def _parse_json(cls, v: dict | str) -> dict:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_serializer("template_data")
    def _serialize_json(self, template_data: dict) -> str:
        return json.dumps(template_data, ensure_ascii=False)

    def mark_sent(self) -> None:
        """Marca el trabajo como enviado."""
        self.status = "sent"
        self.sent_at = datetime.now(timezone.utc).isoformat()
        self.error = None

    def mark_failed(self, error_msg: str) -> None:
        """Marca el trabajo como fallido."""
        self.status = "failed"
        self.sent_at = datetime.now(timezone.utc).isoformat()
        self.error = error_msg

    @classmethod
    def csv_header(cls) -> list[str]:
        """Devuelve los nombres de columna para el CSV."""
        return [
            "id",
            "template_name",
            "recipient",
            "subject",
            "template_data",
            "status",
            "created_at",
            "sent_at",
            "error",
        ]

    def to_csv_row(self) -> dict[str, str]:
        """Serializa el trabajo como diccionario para CSV."""
        return {
            "id": self.id,
            "template_name": self.template_name,
            "recipient": self.recipient,
            "subject": self.subject,
            "template_data": self._serialize_json(self.template_data),
            "status": self.status,
            "created_at": self.created_at,
            "sent_at": self.sent_at or "",
            "error": self.error or "",
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "EmailJob":
        """Crea una instancia desde una fila del CSV."""
        return cls(
            id=row["id"],
            template_name=row["template_name"],
            recipient=row["recipient"],
            subject=row["subject"],
            template_data=row["template_data"],
            status=row["status"],  # type: ignore[arg-type]
            created_at=row["created_at"],
            sent_at=row["sent_at"] or None,
            error=row["error"] or None,
        )
