import json
import os

from models import Asignacion, Horario
from restricciones import RESTRICCIONES_DURAS
from rutas import DIR_DATOS, RUTA_PUBLICADO
from solver import GeneradorHorarios


def guardar_json(ruta, horario):
    datos = [
        {
            "materia": a.sesion.materia.codigo,
            "nivel": a.sesion.nivel.numero,
            "indice": a.sesion.indice,
            "docente": a.docente.id,
            "aula": a.aula.id,
            "dia": a.dia,
            "bloque_inicio": a.bloque_inicio,
        }
        for a in horario.asignaciones
    ]
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "asignaciones": datos}, f, ensure_ascii=False, indent=2)


def cargar_json(ruta, niveles, docentes, aulas):
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = json.load(f)

    sesiones = GeneradorHorarios(niveles, docentes, aulas)._construir_sesiones()
    por_clave = {(s.materia.codigo, s.nivel.numero, s.indice): s for s in sesiones}
    por_docente = {d.id: d for d in docentes}
    por_aula = {a.id: a for a in aulas}

    registros = contenido["asignaciones"]
    if len(registros) != len(sesiones):
        raise ValueError("El archivo no corresponde a los datos actuales (cantidad de sesiones distinta).")

    horario = Horario()
    for r in registros:
        clave = (r["materia"], r["nivel"], r["indice"])
        if clave not in por_clave or r["docente"] not in por_docente or r["aula"] not in por_aula:
            raise ValueError("El archivo contiene sesiones, docentes o aulas que no existen en los datos actuales.")
        sesion = por_clave[clave]
        asignacion = Asignacion(sesion=sesion, docente=por_docente[r["docente"]],
                                aula=por_aula[r["aula"]], dia=r["dia"],
                                bloque_inicio=r["bloque_inicio"])
        for restriccion in RESTRICCIONES_DURAS:
            if not restriccion.cumple(horario, asignacion.docente, asignacion.aula,
                                      sesion.nivel, asignacion.dia, asignacion.bloques):
                raise ValueError("El archivo contiene un horario con choques.")
        horario.agregar(asignacion)
    return horario


def publicar(horario):
    os.makedirs(DIR_DATOS, exist_ok=True)
    guardar_json(RUTA_PUBLICADO, horario)


def cargar_publicado(niveles, docentes, aulas):
    if not os.path.exists(RUTA_PUBLICADO):
        return None
    return cargar_json(RUTA_PUBLICADO, niveles, docentes, aulas)
