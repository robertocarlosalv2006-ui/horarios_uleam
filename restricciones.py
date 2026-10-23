"""
restricciones.py
Restricciones del problema modeladas como clases (POO), para que el motor
de backtracking no tenga la lógica de negocio "quemada" y se puedan agregar
o quitar reglas fácilmente.

- RestriccionDura: obligatoria. Si se incumple, la asignación no es válida.
- RestriccionBlanda: preferencia. No invalida una asignación, pero suma un
  "costo" que la fase de optimización trata de reducir.
"""

from abc import ABC, abstractmethod

from models import Horario, Asignacion, Docente, Aula, Nivel


# ---------------------------------------------------------------------------
# Restricciones duras
# ---------------------------------------------------------------------------

class RestriccionDura(ABC):
    @abstractmethod
    def cumple(self, horario: Horario, docente: Docente, aula: Aula,
               nivel: Nivel, dia: int, bloques: list) -> bool:
        """True si asignar en (dia, bloques) con este docente/aula es válido."""
        raise NotImplementedError


class DocenteSinChoque(RestriccionDura):
    """Un docente no puede dictar dos clases al mismo tiempo."""

    def cumple(self, horario, docente, aula, nivel, dia, bloques):
        return horario.docente_libre(docente, dia, bloques)


class AulaSinChoque(RestriccionDura):
    """Un aula no puede tener dos clases al mismo tiempo."""

    def cumple(self, horario, docente, aula, nivel, dia, bloques):
        return horario.aula_libre(aula, dia, bloques)


class NivelSinChoque(RestriccionDura):
    """Un nivel/paralelo no puede tener dos materias al mismo tiempo."""

    def cumple(self, horario, docente, aula, nivel, dia, bloques):
        return horario.nivel_libre(nivel, dia, bloques)


class DocenteDisponible(RestriccionDura):
    """El docente debe estar disponible en todos los bloques requeridos."""

    def cumple(self, horario, docente, aula, nivel, dia, bloques):
        return all(docente.disponible(dia, b) for b in bloques)


class AulaCompatible(RestriccionDura):
    """El tipo de aula debe ser compatible con la materia (lab / normal)."""

    def cumple(self, horario, docente, aula, nivel, dia, bloques):
        # se valida en el solver directamente contra la materia; aquí se deja
        # como parte del conjunto de restricciones por completitud/documentación
        return True


RESTRICCIONES_DURAS = [
    DocenteSinChoque(),
    AulaSinChoque(),
    NivelSinChoque(),
    DocenteDisponible(),
]


# ---------------------------------------------------------------------------
# Restricciones blandas (preferencias, se usan en la fase de optimización)
# ---------------------------------------------------------------------------

class RestriccionBlanda(ABC):
    @abstractmethod
    def costo(self, horario: Horario) -> int:
        """Entre más alto, peor es el horario respecto a esta preferencia."""
        raise NotImplementedError


class MinimizarHuecos(RestriccionBlanda):
    """Penaliza los 'huecos' (horas libres entre clases) de cada nivel por día."""

    def costo(self, horario: Horario) -> int:
        total = 0
        por_nivel_dia = {}
        for a in horario.asignaciones:
            clave = (a.sesion.nivel.numero, a.dia)
            por_nivel_dia.setdefault(clave, []).extend(a.bloques)

        for bloques_ocupados in por_nivel_dia.values():
            bloques_ocupados = sorted(set(bloques_ocupados))
            for i in range(1, len(bloques_ocupados)):
                hueco = bloques_ocupados[i] - bloques_ocupados[i - 1] - 1
                if hueco > 0:
                    total += hueco
        return total


class BalanceCargaDocente(RestriccionBlanda):
    """Penaliza que un docente tenga muchas más horas un día que otro."""

    def costo(self, horario: Horario) -> int:
        horas_por_docente_dia = {}
        for a in horario.asignaciones:
            clave = (a.docente.id, a.dia)
            horas_por_docente_dia[clave] = horas_por_docente_dia.get(clave, 0) + a.sesion.duracion

        por_docente = {}
        for (docente_id, _dia), horas in horas_por_docente_dia.items():
            por_docente.setdefault(docente_id, []).append(horas)

        total = 0
        for horas_lista in por_docente.values():
            if len(horas_lista) > 1:
                total += max(horas_lista) - min(horas_lista)
        return total


RESTRICCIONES_BLANDAS = [
    MinimizarHuecos(),
    BalanceCargaDocente(),
]
