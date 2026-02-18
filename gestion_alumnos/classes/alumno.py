from dataclasses import dataclass, field
from typing import Optional, List
from gestion_alumnos.util import crea_emails_dominio  # Import específico


@dataclass
class Alumno:
    """Representa un alumno del sistema de gestión."""
    
    id_alumno: int
    id_tipo_documento: int  # tipo de documento
    documento: str          # número de DNI, NIE...
    nombre: str
    p_apellido: str              # primer apellido
    s_apellido: Optional[str] = None  # segundo apellido
    email_sigad: str
    centros: List = field(default_factory=list, repr=False)
    
    # Atributo calculado en post-init
    email_dominio: str = field(init=False, repr=True)

    def __post_init__(self):
        """Inicializa campos calculados después de la construcción."""
        self.email_dominio = crea_emails_dominio(
            self.nombre, self.p_apellido, self.s_apellido, self.documento
        )

    @property
    def apellidos(self) -> str:
        """Devuelve apellidos completos (p_apellido + s_apellido si existe)."""
        if self.s_apellido:
            return f"{self.p_apellido} {self.s_apellido}"
        return self.p_apellido

    def add_centro(self, centro) -> None:
        """Añade un centro a la lista de centros del alumno."""
        self.centros.append(centro)

    def __repr__(self) -> str:
        """Representación legible para debug."""
        centros_repr = "\n\t".join(repr(c) for c in self.centros)
        return (
            f"Alumno(id={self.id_alumno}, doc={self.documento}, "
            f"nombre='{self.nombre}', apellidos='{self.apellidos}', "
            f"email_sigad='{self.email_sigad}', email_dominio='{self.email_dominio}'"
            f"{f'\n\t{centros_repr}' if self.centros else ''})"
        )