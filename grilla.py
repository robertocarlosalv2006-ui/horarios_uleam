import ttkbootstrap as tb

from models import DIAS, TOTAL_BLOQUES_DIA, hora_inicio


# ---------------------------------------------------------------------------
# Widget reutilizable: una grilla semanal (días x horas)
# ---------------------------------------------------------------------------

class GrillaHorario(tb.Frame):
    """Grilla visual de horario: filas = horas, columnas = días.
    Las sesiones de más de 1 hora ocupan varias filas (rowspan)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._celdas = []
        self._construir_cabecera()

    def _construir_cabecera(self):
        tb.Label(self, text="Hora", bootstyle="inverse-dark", anchor="center",
                  font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="nsew", padx=1, pady=1, ipady=4)

        for i, dia in enumerate(DIAS):
            tb.Label(self, text=dia, bootstyle="inverse-dark", anchor="center",
                      font=("Segoe UI", 10, "bold")).grid(
                row=0, column=i + 1, sticky="nsew", padx=1, pady=1, ipady=4)

        for b in range(TOTAL_BLOQUES_DIA):
            tb.Label(self, text=hora_inicio(b), anchor="center",
                      bootstyle="secondary", font=("Segoe UI", 9)).grid(
                row=b + 1, column=0, sticky="nsew", padx=1, pady=1)

        self.columnconfigure(0, weight=1, minsize=60)
        for c in range(1, len(DIAS) + 1):
            self.columnconfigure(c, weight=2, minsize=120, uniform="dia")
        for r in range(TOTAL_BLOQUES_DIA + 1):
            self.rowconfigure(r, weight=1, minsize=36)

    def mostrar(self, asignaciones, etiqueta_extra=None):
        """Dibuja las asignaciones recibidas. etiqueta_extra(asignacion) -> str
        añade una segunda línea de texto a la celda (ej. el nombre del docente)."""
        for w in self._celdas:
            w.destroy()
        self._celdas = []

        ocupados = set()
        for a in asignaciones:
            for b in a.bloques:
                ocupados.add((a.dia, b))

        for a in sorted(asignaciones, key=lambda x: (x.dia, x.bloque_inicio)):
            estilo = "inverse-warning" if a.sesion.materia.requiere_laboratorio else "inverse-info"
            lineas = [a.sesion.materia.codigo]
            if etiqueta_extra:
                lineas.append(etiqueta_extra(a))
            lineas.append(a.aula.nombre)

            lbl = tb.Label(self, text="\n".join(lineas), bootstyle=estilo,
                             anchor="center", justify="center", font=("Segoe UI", 8))
            lbl.grid(row=a.bloque_inicio + 1, column=a.dia + 1,
                      rowspan=a.sesion.duracion, sticky="nsew", padx=1, pady=1)
            self._celdas.append(lbl)

        for dia_idx in range(len(DIAS)):
            for b in range(TOTAL_BLOQUES_DIA):
                if (dia_idx, b) not in ocupados:
                    lbl = tb.Label(self, text="", bootstyle="light")
                    lbl.grid(row=b + 1, column=dia_idx + 1, sticky="nsew", padx=1, pady=1)
                    self._celdas.append(lbl)
