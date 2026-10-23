"""
solver.py
Motor de generación de horarios mediante backtracking con:
  - Heurística MRV (Minimum Remaining Values) para elegir qué sesión asignar.
  - Forward checking: al asignar, se podan de los dominios restantes las
    opciones que quedarían en conflicto.
  - Una fase posterior de optimización local que reduce huecos en los
    horarios usando las restricciones blandas.

No usa librerías externas de resolución de restricciones (CSP hecho a mano).
"""

import copy
import time
from typing import Optional

from models import (
    Horario, Asignacion, Sesion, Nivel,
    BLOQUES_MATUTINA, BLOQUES_VESPERTINA,
)
from restricciones import RESTRICCIONES_DURAS, RESTRICCIONES_BLANDAS


class SinSolucionError(Exception):
    """Se lanza cuando el backtracking agota todas las opciones."""
    pass


class GeneradorHorarios:

    def __init__(self, niveles: list, docentes: list, aulas: list,
                 max_pasos: int = 400_000):
        self.niveles = niveles
        self.docentes = docentes
        self.aulas = aulas
        self.max_pasos = max_pasos   # límite de seguridad para no colgar la app
        self._pasos = 0
        self.tiempo_generacion = 0.0
        self.backtracks = 0

    # ------------------------------------------------------------------
    # 1. Construcción de variables (sesiones) y dominios
    # ------------------------------------------------------------------

    def _construir_sesiones(self) -> list:
        sesiones = []
        for nivel in self.niveles:
            for materia in nivel.materias:
                horas_restantes = materia.horas_semanales
                indice = 1
                while horas_restantes > 0:
                    duracion = min(2, horas_restantes)
                    horas_restantes -= duracion
                    sesiones.append(Sesion(materia=materia, nivel=nivel,
                                            duracion=duracion, indice=indice))
                    indice += 1
        return sesiones

    def _posiciones_validas(self, duracion: int):
        """Genera (dia, bloque_inicio) válidos: la sesión no puede cruzar
        el límite entre jornada matutina y vespertina."""
        for dia in range(5):
            for jornada in (BLOQUES_MATUTINA, BLOQUES_VESPERTINA):
                ultimo_inicio_valido = jornada[-1] - duracion + 1
                for inicio in range(jornada[0], ultimo_inicio_valido + 1):
                    yield dia, inicio

    def _construir_dominios(self, sesiones: list) -> dict:
        dominios = {}
        for s in sesiones:
            docentes_validos = [d for d in self.docentes if d.puede_dictar(s.materia)]
            aulas_validas = [a for a in self.aulas if a.apta_para(s.materia)]
            candidatos = []
            for dia, inicio in self._posiciones_validas(s.duracion):
                bloques = list(range(inicio, inicio + s.duracion))
                for docente in docentes_validos:
                    if not all(docente.disponible(dia, b) for b in bloques):
                        continue
                    for aula in aulas_validas:
                        candidatos.append((dia, inicio, docente, aula))
            dominios[s] = candidatos
        return dominios

    # ------------------------------------------------------------------
    # 2. Backtracking con MRV + forward checking
    # ------------------------------------------------------------------

    def _es_consistente(self, horario: Horario, sesion: Sesion, opcion) -> bool:
        dia, inicio, docente, aula = opcion
        bloques = list(range(inicio, inicio + sesion.duracion))
        return all(
            r.cumple(horario, docente, aula, sesion.nivel, dia, bloques)
            for r in RESTRICCIONES_DURAS
        )

    def _podar_dominios(self, dominios: dict, asignadas: dict, asignacion: Asignacion):
        """Forward checking: quita de los dominios de las sesiones aún no
        asignadas las opciones que ahora chocarían con 'asignacion'.
        Devuelve lo eliminado, para poder restaurarlo si se hace backtrack."""
        eliminados = {}
        for sesion, opciones in dominios.items():
            if sesion in asignadas:
                continue
            sobrevivientes = []
            quitados = []
            for opcion in opciones:
                dia, inicio, docente, aula = opcion
                bloques = set(range(inicio, inicio + sesion.duracion))
                choque_docente = (docente.id == asignacion.docente.id and dia == asignacion.dia
                                   and bloques & set(asignacion.bloques))
                choque_aula = (aula.id == asignacion.aula.id and dia == asignacion.dia
                               and bloques & set(asignacion.bloques))
                choque_nivel = (sesion.nivel.numero == asignacion.sesion.nivel.numero
                                and dia == asignacion.dia and bloques & set(asignacion.bloques))
                if choque_docente or choque_aula or choque_nivel:
                    quitados.append(opcion)
                else:
                    sobrevivientes.append(opcion)
            if quitados:
                eliminados[sesion] = quitados
                dominios[sesion] = sobrevivientes
        return eliminados

    def _restaurar_dominios(self, dominios: dict, eliminados: dict):
        for sesion, opciones in eliminados.items():
            dominios[sesion].extend(opciones)

    def _backtrack(self, dominios: dict, asignadas: dict, horario: Horario) -> bool:
        self._pasos += 1
        if self._pasos > self.max_pasos:
            raise SinSolucionError(
                "Se alcanzó el límite de pasos de búsqueda sin encontrar solución. "
                "Revisa la disponibilidad de docentes/aulas o reduce la carga horaria.")

        pendientes = [s for s in dominios if s not in asignadas]
        if not pendientes:
            return True  # todas las sesiones quedaron asignadas

        # Heurística MRV: la sesión con menos opciones disponibles primero.
        sesion = min(pendientes, key=lambda s: len(dominios[s]))

        # Orden de valores: preferir el día menos cargado para el nivel y el
        # docente, para repartir las clases entre la semana en vez de
        # amontonarlas al inicio.
        opciones = sorted(
            dominios[sesion],
            key=lambda o: (
                horario.horas_nivel_en_dia(sesion.nivel.numero, o[0]),
                horario.horas_docente_en_dia(o[2].id, o[0]),
            ),
        )

        for opcion in opciones:
            if not self._es_consistente(horario, sesion, opcion):
                continue
            dia, inicio, docente, aula = opcion
            asignacion = Asignacion(sesion=sesion, docente=docente, aula=aula,
                                     dia=dia, bloque_inicio=inicio)
            horario.agregar(asignacion)
            asignadas[sesion] = asignacion
            eliminados = self._podar_dominios(dominios, asignadas, asignacion)

            if self._backtrack(dominios, asignadas, horario):
                return True

            # deshacer (backtrack)
            self.backtracks += 1
            self._restaurar_dominios(dominios, eliminados)
            del asignadas[sesion]
            horario.quitar(asignacion)

        return False

    # ------------------------------------------------------------------
    # 3. Optimización local (restricciones blandas)
    # ------------------------------------------------------------------

    def _costo_total(self, horario: Horario) -> int:
        return sum(r.costo(horario) for r in RESTRICCIONES_BLANDAS)

    def _optimizar(self, horario: Horario, iteraciones: int = 300):
        """Intenta mover sesiones a un bloque más temprano del mismo día/jornada
        para reducir huecos, siempre que no rompa ninguna restricción dura."""
        mejor_costo = self._costo_total(horario)

        for _ in range(iteraciones):
            mejorado = False
            for asignacion in list(horario.asignaciones):
                sesion = asignacion.sesion
                jornada = BLOQUES_MATUTINA if asignacion.bloque_inicio in BLOQUES_MATUTINA else BLOQUES_VESPERTINA
                ultimo_inicio_valido = jornada[-1] - sesion.duracion + 1

                for nuevo_inicio in range(jornada[0], asignacion.bloque_inicio):
                    if nuevo_inicio > ultimo_inicio_valido:
                        continue
                    nuevos_bloques = list(range(nuevo_inicio, nuevo_inicio + sesion.duracion))

                    horario.quitar(asignacion)
                    candidata = Asignacion(sesion=sesion, docente=asignacion.docente,
                                            aula=asignacion.aula, dia=asignacion.dia,
                                            bloque_inicio=nuevo_inicio)
                    valido = all(
                        r.cumple(horario, candidata.docente, candidata.aula,
                                 sesion.nivel, candidata.dia, nuevos_bloques)
                        for r in RESTRICCIONES_DURAS
                    )
                    if valido:
                        horario.agregar(candidata)
                        nuevo_costo = self._costo_total(horario)
                        if nuevo_costo < mejor_costo:
                            mejor_costo = nuevo_costo
                            mejorado = True
                            break
                        else:
                            horario.quitar(candidata)
                            horario.agregar(asignacion)
                    else:
                        horario.agregar(asignacion)
                else:
                    continue
                break
            if not mejorado:
                break
        return mejor_costo

    # ------------------------------------------------------------------
    # 4. Punto de entrada público
    # ------------------------------------------------------------------

    def generar(self, optimizar: bool = True) -> Horario:
        inicio = time.time()
        self._pasos = 0
        self.backtracks = 0

        sesiones = self._construir_sesiones()
        dominios = self._construir_dominios(sesiones)
        horario = Horario()
        asignadas = {}

        encontrado = self._backtrack(dominios, asignadas, horario)
        if not encontrado:
            raise SinSolucionError(
                "No se encontró un horario factible con los datos actuales "
                "(revisa disponibilidad de docentes, cantidad de aulas o carga horaria).")

        if optimizar:
            self._optimizar(horario)

        self.tiempo_generacion = time.time() - inicio
        return horario
