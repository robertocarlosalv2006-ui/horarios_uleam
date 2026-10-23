import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT
from ttkbootstrap.dialogs import Messagebox

from models import (
    DIAS, TOTAL_BLOQUES_DIA, BLOQUES_MATUTINA, BLOQUES_VESPERTINA,
    Asignacion, hora_fin, hora_inicio,
)
from restricciones import RESTRICCIONES_DURAS

MENSAJES = {
    "DocenteSinChoque": "El docente ya tiene otra clase en ese horario.",
    "AulaSinChoque": "El aula ya está ocupada en ese horario.",
    "NivelSinChoque": "El nivel ya tiene otra materia en ese horario.",
    "DocenteDisponible": "El docente no está disponible en ese horario.",
}


def validar_cambio(horario, asignacion, dia, inicio, docente, aula):
    sesion = asignacion.sesion
    bloques = list(range(inicio, inicio + sesion.duracion))
    jornada = BLOQUES_MATUTINA if inicio in BLOQUES_MATUTINA else BLOQUES_VESPERTINA
    if bloques[-1] not in jornada:
        return "La sesión no puede cruzar el cambio de jornada (13:00) ni salirse del horario."
    if not docente.puede_dictar(sesion.materia):
        return "El docente no está habilitado para esta materia."
    if not aula.apta_para(sesion.materia):
        return "El aula no es compatible con el tipo de materia."

    horario.quitar(asignacion)
    try:
        for restriccion in RESTRICCIONES_DURAS:
            if not restriccion.cumple(horario, docente, aula, sesion.nivel, dia, bloques):
                return MENSAJES.get(type(restriccion).__name__, "Incumple una restricción obligatoria.")
    finally:
        horario.agregar(asignacion)
    return None


def aplicar_cambio(horario, asignacion, dia, inicio, docente, aula):
    horario.quitar(asignacion)
    nueva = Asignacion(sesion=asignacion.sesion, docente=docente, aula=aula,
                       dia=dia, bloque_inicio=inicio)
    horario.agregar(nueva)
    return nueva


class DialogoEdicion(tb.Toplevel):

    def __init__(self, master, horario, asignacion, docentes, aulas):
        super().__init__(master)
        self.title("Editar sesión")
        self.resizable(False, False)
        self.transient(master)

        self.horario = horario
        self.asignacion = asignacion
        self.resultado = None

        materia = asignacion.sesion.materia
        duracion = asignacion.sesion.duracion
        self.docentes = [d for d in docentes if d.puede_dictar(materia)]
        self.aulas = [a for a in aulas if a.apta_para(materia)]

        marco = tb.Frame(self, padding=20)
        marco.pack(fill=BOTH, expand=True)

        tb.Label(marco, text=str(asignacion.sesion), font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        tb.Label(marco, text=materia.nombre, bootstyle="secondary").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        horas = [f"{hora_inicio(b)} - {hora_fin(b + duracion - 1)}" for b in range(TOTAL_BLOQUES_DIA)]

        self.combo_dia = self._campo(marco, 2, "Día:", DIAS, asignacion.dia)
        self.combo_hora = self._campo(marco, 3, "Hora:", horas, asignacion.bloque_inicio)
        self.combo_docente = self._campo(
            marco, 4, "Docente:", [d.nombre for d in self.docentes],
            self.docentes.index(asignacion.docente))
        self.combo_aula = self._campo(
            marco, 5, "Aula:", [a.nombre for a in self.aulas],
            self.aulas.index(asignacion.aula))

        botones = tb.Frame(marco)
        botones.grid(row=6, column=0, columnspan=2, sticky="e", pady=(16, 0))
        tb.Button(botones, text="Cancelar", bootstyle="secondary-outline",
                  command=self.destroy).pack(side=LEFT, padx=(0, 8))
        tb.Button(botones, text="Guardar cambio", bootstyle="success",
                  command=self._guardar).pack(side=LEFT)

        self.wait_visibility()
        self.grab_set()

    def _campo(self, marco, fila, texto, valores, actual):
        tb.Label(marco, text=texto, font=("Segoe UI", 10, "bold")).grid(
            row=fila, column=0, sticky="w", padx=(0, 12), pady=4)
        combo = tb.Combobox(marco, values=valores, state="readonly", width=30)
        combo.current(actual)
        combo.grid(row=fila, column=1, sticky="w", pady=4)
        return combo

    def _guardar(self):
        dia = self.combo_dia.current()
        inicio = self.combo_hora.current()
        docente = self.docentes[self.combo_docente.current()]
        aula = self.aulas[self.combo_aula.current()]

        error = validar_cambio(self.horario, self.asignacion, dia, inicio, docente, aula)
        if error:
            Messagebox.show_error(error, "Cambio no válido", parent=self)
            return
        self.resultado = (dia, inicio, docente, aula)
        self.destroy()


def editar_asignacion(master, horario, asignacion, docentes, aulas):
    dialogo = DialogoEdicion(master, horario, asignacion, docentes, aulas)
    master.wait_window(dialogo)
    if dialogo.resultado is None:
        return False
    dia, inicio, docente, aula = dialogo.resultado
    aplicar_cambio(horario, asignacion, dia, inicio, docente, aula)
    return True
