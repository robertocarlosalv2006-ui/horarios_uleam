import os

from auth import RepositorioUsuarios, ADMIN, DOCENTE
from datos_ejemplo import construir_niveles, construir_docentes, construir_aulas
from login import VentanaLogin
from persistencia import publicar
from rutas import RUTA_PUBLICADO
from solver import GeneradorHorarios, SinSolucionError
from gui import Aplicacion
from vistas import VistaDocente, VistaEstudiante


def asegurar_horario_publicado():
    if os.path.exists(RUTA_PUBLICADO):
        return
    generador = GeneradorHorarios(construir_niveles(), construir_docentes(), construir_aulas())
    try:
        publicar(generador.generar())
    except (SinSolucionError, OSError):
        pass


def crear_ventana(usuario, repo):
    if usuario.rol == ADMIN:
        return Aplicacion(usuario, repo)
    if usuario.rol == DOCENTE:
        return VistaDocente(usuario)
    return VistaEstudiante(usuario)


def main():
    repo = RepositorioUsuarios(construir_docentes(), construir_niveles())
    asegurar_horario_publicado()

    while True:
        login = VentanaLogin(repo)
        login.mainloop()
        if login.usuario is None:
            break
        ventana = crear_ventana(login.usuario, repo)
        ventana.mainloop()
        if not ventana.cerrar_sesion:
            break


if __name__ == "__main__":
    main()
