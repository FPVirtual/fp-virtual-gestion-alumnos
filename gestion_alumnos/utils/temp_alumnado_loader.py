import json
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
from sqlalchemy.orm import sessionmaker, scoped_session
from typing import List, Dict, Any

class TempAlumnadoLoader:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False, pool_pre_ping=True)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.metadata = MetaData()
        self.temp_table = self._define_temp_table()
        self._create_table()

    def _define_temp_table(self) -> Table:
        return Table(
            'temp_alumnos', self.metadata,
            Column('idAlumno', Integer),
            Column('idTipoDocumento', Integer),
            Column('documento', String(20)),
            Column('email', String(255)),
            prefixes=['TEMPORARY']
        )

    def _create_table(self):
        # Crear la tabla sin todavía cerrar la sesión
        self.metadata.create_all(self.engine)

    def load_json(self, json_path: str) -> List[Dict[str, Any]]:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [
            {
                'idAlumno': alumno['idAlumno'],
                'idTipoDocumento': alumno['idTipoDocumento'],
                'documento': alumno['documento'],
                'email': alumno['email']
            }
            for alumno in data['alumnos']
        ]

    def populate(self, json_path: str) -> int:
        values = self.load_json(json_path)
        self.Session.execute(self.temp_table.insert(), values)
        self.Session.commit()
        return len(values)

    def query(self, limit: int = 5):
        return self.Session.execute(self.temp_table.select().limit(limit)).fetchall()

    def close(self):
        self.Session.remove()
        self.engine.dispose()