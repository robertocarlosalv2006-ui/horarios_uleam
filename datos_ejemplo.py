"""
datos_ejemplo.py
Datos de ejemplo para el sistema: malla curricular real de Ingeniería en
Software (ULEAM, pensum 2022), docentes y aulas ficticias con restricciones
razonables para que el problema de asignación sea representativo.
"""

from models import Materia, Docente, Aula, Nivel, TipoAula

# ---------------------------------------------------------------------------
# 1. Malla curricular -> horas semanales derivadas de los créditos oficiales
#    (144 créditos ~ 3h/sem, 192 ~ 4h/sem, 96 ~ 2h/sem, 48 ~ 1h/sem)
# ---------------------------------------------------------------------------

# (codigo, nombre, horas_semanales, requiere_laboratorio)
_MALLA = {
    1: [
        ("IS-101", "Fundamentos de la Ingeniería de Software", 3, False),
        ("IS-102", "Arquitectura del Computador", 3, False),
        ("IS-103", "Algoritmos y Lógica de Programación", 4, True),
        ("IS-104", "Álgebra Lineal", 3, False),
        ("CAT-101", "Cátedra Alfaro", 2, False),
    ],
    2: [
        ("IS-201", "Ingeniería de Requisitos", 3, False),
        ("IS-202", "Sistemas Operativos", 3, False),
        ("IS-203", "Programación Estructurada", 4, True),
        ("IS-204", "Matemática Discreta", 3, False),
        ("ECO-201", "Economía Global", 2, False),
    ],
    3: [
        ("IS-301", "Modelado Orientado a Objetos", 3, False),
        ("IS-302", "Redes de Computadoras", 3, True),
        ("IS-303", "Programación Orientada a Objetos", 3, True),
        ("IS-304", "Estructura de Datos", 3, True),
        ("IS-305", "Bases de Datos", 3, True),
    ],
    4: [
        ("IS-402", "Administración de Servidores", 3, True),
        ("IS-403", "Aplicaciones para el Cliente Web", 3, True),
        ("IS-404", "Administración de Bases de Datos Distribuidas", 4, True),
        ("IS-405", "Estadística para Ingeniería", 3, False),
        ("INN-401", "Innovación, Emprendimiento y Liderazgo", 2, False),
    ],
    5: [
        ("IS-501", "Arquitectura del Software", 3, False),
        ("IS-502", "Interfaz Humano-Computador", 2, False),
        ("IS-503", "Aplicación para el Servidor Web", 3, True),
        ("IS-504", "Minería de Datos", 3, True),
        ("IS-505", "Modelado Ágil de Software", 3, False),
        ("IS-507", "Prácticas de Servicio Comunitario I", 1, False),
    ],
    6: [
        ("IS-601", "Usabilidad y Accesibilidad", 2, False),
        ("IS-602", "Ciclos de Desarrollo de Software Seguro", 3, False),
        ("IS-603", "Aplicaciones Móviles Nativas", 3, True),
        ("IS-604", "Visualización de Datos", 3, True),
        ("IS-605", "Metodología de Investigación", 3, False),
        ("IS-606", "Prácticas de Servicio Comunitario II", 1, False),
    ],
    7: [
        ("IS-701", "Diseño Centrado en el Usuario", 2, False),
        ("IS-702", "Auditoría de Software", 2, False),
        ("IS-703", "Aplicaciones Móviles Híbridas", 2, True),
        ("IS-704", "Analítica de Negocio", 2, False),
        ("IS-706", "Diseño del Trabajo de Integración Curricular", 3, False),
        ("IS-707", "Prácticas Laborales I", 4, False),
    ],
    8: [
        ("IS-801", "Gestión de Proyectos de Software", 3, False),
        ("IS-802", "Hacking Ético", 2, True),
        ("IS-803", "Integración e Implementación de Software", 2, True),
        ("IS-804", "Calidad de Software", 3, False),
        ("IS-805", "Desarrollo del Trabajo de Integración Curricular", 3, False),
        ("IS-806", "Prácticas Laborales II", 2, False),
    ],
}


def construir_niveles() -> list:
    """Construye los 8 niveles con sus materias a partir de la malla curricular."""
    niveles = []
    for numero, materias_raw in _MALLA.items():
        materias = [
            Materia(codigo=c, nombre=n, nivel=numero, horas_semanales=h, requiere_laboratorio=lab)
            for c, n, h, lab in materias_raw
        ]
        niveles.append(Nivel(numero=numero, materias=materias, num_estudiantes=30))
    return niveles


# ---------------------------------------------------------------------------
# 2. Docentes: cada uno habilitado para materias afines a su área.
#    Se incluye un par con disponibilidad restringida para que el CSP tenga
#    restricciones reales que forzar (no solo restricciones triviales).
# ---------------------------------------------------------------------------

def construir_docentes() -> list:
    docentes = [
        Docente("D01", "Ing. Carlos Zambrano", {
            "IS-101", "IS-201", "IS-301", "IS-501"}),
        Docente("D02", "Ing. María Cedeño", {
            "IS-103", "IS-203", "IS-303", "IS-304"}),
        Docente("D03", "Ing. Jorge Mendoza", {
            "IS-102", "IS-202", "IS-302", "IS-402"}),
        Docente("D04", "Ing. Alexandra Vera", {
            "IS-305", "IS-404", "IS-504", "IS-604"}),
        Docente("D05", "Ing. Danilo Arévalo", {
            "IS-104", "IS-204", "IS-405", "ECO-201"}),
        Docente("D06", "Ing. Rocío Villamar", {
            "IS-403", "IS-503", "IS-603", "IS-703"}),
        Docente("D07", "Ing. Wilian Delgado", {
            "IS-502", "IS-601", "IS-701", "IS-801"}),
        Docente("D08", "Ing. Klever Reyes", {
            "IS-505", "IS-602", "IS-702", "IS-804"}),
        Docente("D09", "Ing. Renelmo Minaya", {
            "IS-802", "IS-803", "IS-704", "IS-605"}),
        Docente("D10", "Lic. Bella Barreiro", {
            "CAT-101", "INN-401", "IS-507", "IS-606",
            "IS-706", "IS-707", "IS-805", "IS-806"}),
    ]

    # Ejemplo de restricción de disponibilidad real: este docente solo
    # trabaja en jornada matutina (bloquea todos los bloques vespertinos).
    for dia in range(5):
        for bloque in range(6, 12):
            docentes[4].bloqueos_no_disponible.add((dia, bloque))   # D05: solo mañanas

    # Este docente no puede dictar los viernes (día índice 4).
    for bloque in range(0, 12):
        docentes[8].bloqueos_no_disponible.add((4, bloque))         # D09: no viernes

    return docentes


# ---------------------------------------------------------------------------
# 3. Aulas: 4 normales + 2 laboratorios
# ---------------------------------------------------------------------------

def construir_aulas() -> list:
    return [
        Aula("A1", "Aula A1", 35, TipoAula.NORMAL),
        Aula("A2", "Aula A2", 35, TipoAula.NORMAL),
        Aula("A3", "Aula A3", 35, TipoAula.NORMAL),
        Aula("A4", "Aula A4", 35, TipoAula.NORMAL),
        Aula("L1", "Laboratorio L1", 30, TipoAula.LABORATORIO),
        Aula("L2", "Laboratorio L2", 30, TipoAula.LABORATORIO),
    ]
