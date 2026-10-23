"""
models.py
Modelo de dominio (POO) para el sistema de distribución de horarios.

Contiene las clases base que representan las entidades del problema:
Materia, Docente, Aula, Nivel, Sesion, Asignacion y Horario.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Constantes de tiempo
# ---------------------------------------------------------------------------

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

# 12 bloques de 1 hora por día: 07h00-13h00 (matutina) + 13h00-19h00 (vespertina)
# índice de bloque 0..11  ->  hora de inicio = 7 + índice
TOTAL_BLOQUES_DIA = 12
BLOQUES_MATUTINA = list(range(0, 6))    # 07:00 - 13:00
BLOQUES_VESPERTINA = list(range(6, 12))  # 13:00 - 19:00


def hora_inicio(bloque: int) -> str:
    """Devuelve la hora de inicio de un bloque, ej. bloque 0 -> '07:00'."""
    return f"{7 + bloque:02d}:00"


def hora_fin(bloque: int) -> str:
    return f"{8 + bloque:02d}:00"


def jornada_de_bloque(bloque: int) -> str:
    return "Matutina" if bloque in BLOQUES_MATUTINA else "Vespertina"


# ---------------------------------------------------------------------------
# Enumeraciones
# ---------------------------------------------------------------------------

class TipoAula(Enum):
    NORMAL = "Normal"
    LABORATORIO = "Laboratorio"


# ---------------------------------------------------------------------------
# Entidades del dominio
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Materia:
    codigo: str
    nombre: str
    nivel: int
    horas_semanales: int
    requiere_laboratorio: bool = False

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


@dataclass
class Docente:
    id: str
    nombre: str
    materias_habilitadas: set = field(default_factory=set)  # códigos de Materia
    # Si bloqueos_no_disponible está vacío, el docente está disponible todo el horario.
    # Cada elemento es una tupla (dia_idx, bloque_idx) en la que el docente NO puede dictar.
    bloqueos_no_disponible: set = field(default_factory=set)

    def puede_dictar(self, materia: Materia) -> bool:
        return materia.codigo in self.materias_habilitadas

    def disponible(self, dia: int, bloque: int) -> bool:
        return (dia, bloque) not in self.bloqueos_no_disponible

    def __str__(self) -> str:
        return f"{self.nombre}"


@dataclass
class Aula:
    id: str
    nombre: str
    capacidad: int
    tipo: TipoAula

    def apta_para(self, materia: Materia) -> bool:
        if materia.requiere_laboratorio:
            return self.tipo == TipoAula.LABORATORIO
        return self.tipo == TipoAula.NORMAL

    def __str__(self) -> str:
        return self.nombre


@dataclass
class Nivel:
    numero: int
    materias: list = field(default_factory=list)  # list[Materia]
    num_estudiantes: int = 30

    def __str__(self) -> str:
        return f"Nivel {self.numero}"


@dataclass(frozen=True, eq=False)
class Sesion:
    """
    Una 'sesión' es un bloque continuo de horas que hay que ubicar en el
    horario para una materia de un nivel. Una materia con varias horas
    semanales se reparte en varias sesiones (máx. 2h seguidas por sesión).
    """
    materia: Materia
    nivel: Nivel
    duracion: int   # cantidad de bloques (horas) consecutivos que ocupa
    indice: int     # 1, 2, 3... para distinguir varias sesiones de la misma materia

    def __str__(self) -> str:
        return f"{self.materia.codigo} (N{self.nivel.numero}) sesión {self.indice} [{self.duracion}h]"


@dataclass
class Asignacion:
    """El resultado de ubicar una Sesion en el horario: quién, dónde y cuándo."""
    sesion: Sesion
    docente: Docente
    aula: Aula
    dia: int
    bloque_inicio: int

    @property
    def bloques(self):
        return list(range(self.bloque_inicio, self.bloque_inicio + self.sesion.duracion))

    def __str__(self) -> str:
        return (f"{DIAS[self.dia]} {hora_inicio(self.bloque_inicio)}-"
                f"{hora_fin(self.bloque_inicio + self.sesion.duracion - 1)} | "
                f"{self.sesion.materia.codigo} | {self.docente.nombre} | {self.aula.nombre}")


class Horario:
    """
    Estado del horario en construcción. Mantiene la lista de asignaciones y
    mapas de ocupación (docente/aula/nivel) para verificar conflictos en O(1).
    """

    def __init__(self):
        self.asignaciones: list[Asignacion] = []
        self._ocupado_docente = set()   # (docente_id, dia, bloque)
        self._ocupado_aula = set()      # (aula_id, dia, bloque)
        self._ocupado_nivel = set()     # (nivel_num, dia, bloque)
        # contadores auxiliares usados para repartir la carga entre días
        # (heurística de orden de valores: preferir el día menos cargado)
        self._horas_nivel_dia: dict = {}     # (nivel_num, dia) -> horas ya puestas
        self._horas_docente_dia: dict = {}   # (docente_id, dia) -> horas ya puestas

    def horas_nivel_en_dia(self, nivel_numero: int, dia: int) -> int:
        return self._horas_nivel_dia.get((nivel_numero, dia), 0)

    def horas_docente_en_dia(self, docente_id: str, dia: int) -> int:
        return self._horas_docente_dia.get((docente_id, dia), 0)

    # -- consultas --------------------------------------------------------

    def docente_libre(self, docente: Docente, dia: int, bloques: list) -> bool:
        return all((docente.id, dia, b) not in self._ocupado_docente for b in bloques)

    def aula_libre(self, aula: Aula, dia: int, bloques: list) -> bool:
        return all((aula.id, dia, b) not in self._ocupado_aula for b in bloques)

    def nivel_libre(self, nivel: Nivel, dia: int, bloques: list) -> bool:
        return all((nivel.numero, dia, b) not in self._ocupado_nivel for b in bloques)

    # -- mutaciones ---------------------------------------------------------

    def agregar(self, asignacion: Asignacion) -> None:
        self.asignaciones.append(asignacion)
        for b in asignacion.bloques:
            self._ocupado_docente.add((asignacion.docente.id, asignacion.dia, b))
            self._ocupado_aula.add((asignacion.aula.id, asignacion.dia, b))
            self._ocupado_nivel.add((asignacion.sesion.nivel.numero, asignacion.dia, b))
        clave_n = (asignacion.sesion.nivel.numero, asignacion.dia)
        clave_d = (asignacion.docente.id, asignacion.dia)
        self._horas_nivel_dia[clave_n] = self._horas_nivel_dia.get(clave_n, 0) + asignacion.sesion.duracion
        self._horas_docente_dia[clave_d] = self._horas_docente_dia.get(clave_d, 0) + asignacion.sesion.duracion

    def quitar(self, asignacion: Asignacion) -> None:
        self.asignaciones.remove(asignacion)
        for b in asignacion.bloques:
            self._ocupado_docente.discard((asignacion.docente.id, asignacion.dia, b))
            self._ocupado_aula.discard((asignacion.aula.id, asignacion.dia, b))
            self._ocupado_nivel.discard((asignacion.sesion.nivel.numero, asignacion.dia, b))
        clave_n = (asignacion.sesion.nivel.numero, asignacion.dia)
        clave_d = (asignacion.docente.id, asignacion.dia)
        self._horas_nivel_dia[clave_n] = self._horas_nivel_dia.get(clave_n, 0) - asignacion.sesion.duracion
        self._horas_docente_dia[clave_d] = self._horas_docente_dia.get(clave_d, 0) - asignacion.sesion.duracion

    # -- utilidades de consulta para la interfaz -----------------------------

    def por_nivel(self, numero: int) -> list:
        return [a for a in self.asignaciones if a.sesion.nivel.numero == numero]

    def por_docente(self, docente_id: str) -> list:
        return [a for a in self.asignaciones if a.docente.id == docente_id]

    def por_aula(self, aula_id: str) -> list:
        return [a for a in self.asignaciones if a.aula.id == aula_id]
