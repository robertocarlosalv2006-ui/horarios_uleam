import os

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, X, Y, LEFT, RIGHT

from datos_ejemplo import construir_niveles, construir_docentes, construir_aulas
from grilla import GrillaHorario
from persistencia import cargar_publicado
from rutas import RUTA_PUBLICADO

INTERVALO_MS = 1500


class VistaBase(tb.Window):

    def __init__(self, usuario, titulo, subtitulo):
        super().__init__(title=f"{titulo} — Horarios ULEAM", themename="cosmo",
                         size=(1180, 720), resizable=(True, True))
        self.minsize(1000, 620)
        self.usuario = usuario
        self.cerrar_sesion = False
        self.niveles = construir_niveles()
        self.docentes = construir_docentes()
        self.aulas = construir_aulas()
        self.horario = None
        self._ultima_version = None

        self._construir_barra(titulo, subtitulo)
        self.cuerpo = tb.Frame(self, padding=(15, 0, 15, 15))
        self.cuerpo.pack(fill=BOTH, expand=True)

    def _construir_barra(self, titulo, subtitulo):
        barra = tb.Frame(self, padding=(15, 12))
        barra.pack(fill=X)

        izquierda = tb.Frame(barra)
        izquierda.pack(side=LEFT)
        tb.Label(izquierda, text=titulo, font=("Segoe UI", 17, "bold")).pack(anchor="w")
        self._subtitulo = tb.Label(izquierda, text=subtitulo, bootstyle="secondary",
                                   font=("Segoe UI", 10))
        self._subtitulo.pack(anchor="w")

        derecha = tb.Frame(barra)
        derecha.pack(side=RIGHT)
        tb.Button(derecha, text="Cerrar sesión", bootstyle="danger-outline",
                  command=self._salir).pack(side=RIGHT)
        tb.Button(derecha, text="⟳  Actualizar", bootstyle="primary",
                  command=self.actualizar).pack(side=RIGHT, padx=(0, 8))
        self.lbl_estado = tb.Label(derecha, text="", bootstyle="secondary", font=("Segoe UI", 10))
        self.lbl_estado.pack(side=RIGHT, padx=(0, 15))

    def _tabla(self, padre, columnas, titulos, anchos):
        contenedor = tb.Frame(padre)
        contenedor.pack(fill=BOTH, expand=True)
        tree = tb.Treeview(contenedor, columns=columnas, show="headings",
                           bootstyle="primary", selectmode="browse")
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            tree.heading(col, text=titulo)
            tree.column(col, width=ancho, anchor="w")
        scroll = tb.Scrollbar(contenedor, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)
        return tree

    def _salir(self):
        self.cerrar_sesion = True
        self.destroy()

    def _version_publicada(self):
        try:
            return os.stat(RUTA_PUBLICADO).st_mtime_ns
        except OSError:
            return None

    def _vigilar(self):
        if self._version_publicada() != self._ultima_version:
            self.actualizar()
        self.after(INTERVALO_MS, self._vigilar)

    def iniciar(self):
        self.actualizar()
        self.after(INTERVALO_MS, self._vigilar)

    def actualizar(self):
        self._ultima_version = self._version_publicada()
        try:
            self.horario = cargar_publicado(self.niveles, self.docentes, self.aulas)
        except (ValueError, KeyError, OSError):
            self.horario = None
            self.lbl_estado.configure(text="No se pudo leer el horario", bootstyle="danger")
        else:
            if self.horario is None:
                self.lbl_estado.configure(text="Aún no hay horario publicado", bootstyle="warning")
            else:
                self.lbl_estado.configure(text="Horario actualizado", bootstyle="success")
        self.refrescar()

    def refrescar(self):
        raise NotImplementedError

    def _vaciar(self, tree):
        for iid in tree.get_children():
            tree.delete(iid)


class VistaDocente(VistaBase):

    def __init__(self, usuario):
        super().__init__(usuario, "Panel del docente", f"{usuario.nombre} · Docente")
        self.docente = next(d for d in self.docentes if d.id == usuario.referencia)

        notebook = tb.Notebook(self.cuerpo)
        notebook.pack(fill=BOTH, expand=True)
        tab_horario = tb.Frame(notebook, padding=12)
        tab_materias = tb.Frame(notebook, padding=12)
        notebook.add(tab_horario, text="  Mi horario  ")
        notebook.add(tab_materias, text="  Mis materias  ")

        self.lbl_total = tb.Label(tab_horario, text="", bootstyle="secondary", font=("Segoe UI", 10))
        self.lbl_total.pack(anchor="w", pady=(0, 8))
        self.grilla = GrillaHorario(tab_horario)
        self.grilla.pack(fill=BOTH, expand=True)

        self.tree = self._tabla(
            tab_materias, ("codigo", "materia", "nivel", "horas"),
            ("Código", "Materia", "Nivel", "Horas/semana"), (90, 400, 90, 120))

        self.iniciar()

    def refrescar(self):
        asigs = self.horario.por_docente(self.docente.id) if self.horario else []
        self.grilla.mostrar(asigs, etiqueta_extra=lambda a: f"Nivel {a.sesion.nivel.numero}")

        total = sum(a.sesion.duracion for a in asigs)
        self.lbl_total.configure(
            text=f"Carga semanal: {total} h · {len(asigs)} sesiones" if self.horario else "")

        horas = {}
        for a in asigs:
            clave = (a.sesion.nivel.numero, a.sesion.materia.codigo)
            horas[clave] = horas.get(clave, 0) + a.sesion.duracion
        nombres = {m.codigo: m.nombre for n in self.niveles for m in n.materias}

        self._vaciar(self.tree)
        for (nivel, codigo), h in sorted(horas.items()):
            self.tree.insert("", "end", values=(codigo, nombres[codigo], f"Nivel {nivel}", h))


class VistaEstudiante(VistaBase):

    def __init__(self, usuario):
        super().__init__(usuario, "Panel del estudiante", "")
        self.nivel = next(n for n in self.niveles if str(n.numero) == usuario.referencia)
        self.title(f"Panel del estudiante — Nivel {self.nivel.numero} — Horarios ULEAM")
        self._subtitulo.configure(text=f"{usuario.nombre} · Nivel {self.nivel.numero}")

        notebook = tb.Notebook(self.cuerpo)
        notebook.pack(fill=BOTH, expand=True)
        tab_horario = tb.Frame(notebook, padding=12)
        tab_materias = tb.Frame(notebook, padding=12)
        notebook.add(tab_horario, text="  Mi horario  ")
        notebook.add(tab_materias, text="  Materias  ")

        self.lbl_total = tb.Label(tab_horario, text="", bootstyle="secondary", font=("Segoe UI", 10))
        self.lbl_total.pack(anchor="w", pady=(0, 8))
        self.grilla = GrillaHorario(tab_horario)
        self.grilla.pack(fill=BOTH, expand=True)

        self.tree = self._tabla(
            tab_materias, ("codigo", "materia", "docente", "horas", "tipo"),
            ("Código", "Materia", "Docente", "Horas/semana", "Tipo de aula"),
            (90, 380, 200, 110, 120))

        self.iniciar()

    def refrescar(self):
        asigs = self.horario.por_nivel(self.nivel.numero) if self.horario else []
        self.grilla.mostrar(asigs, etiqueta_extra=lambda a: a.docente.nombre)

        total = sum(a.sesion.duracion for a in asigs)
        self.lbl_total.configure(
            text=f"{total} h semanales · {len(self.nivel.materias)} materias" if self.horario else "")

        horas = {}
        docentes = {}
        for a in asigs:
            codigo = a.sesion.materia.codigo
            horas[codigo] = horas.get(codigo, 0) + a.sesion.duracion
            docentes.setdefault(codigo, set()).add(a.docente.nombre)

        self._vaciar(self.tree)
        for m in self.nivel.materias:
            self.tree.insert("", "end", values=(
                m.codigo, m.nombre, ", ".join(sorted(docentes.get(m.codigo, []))) or "—",
                horas.get(m.codigo, 0),
                "Laboratorio" if m.requiere_laboratorio else "Aula normal"))
