"""
gui.py
Interfaz gráfica del Sistema de Distribución de Horarios, construida con
ttkbootstrap (tema moderno sobre tkinter).
"""

import os
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, X, Y, LEFT, RIGHT
from ttkbootstrap.dialogs import Messagebox

from models import DIAS, TOTAL_BLOQUES_DIA, hora_inicio, hora_fin
from datos_ejemplo import construir_niveles, construir_docentes, construir_aulas
from solver import GeneradorHorarios, SinSolucionError
from restricciones import RESTRICCIONES_BLANDAS
from edicion import editar_asignacion
from persistencia import guardar_json, cargar_json, publicar, cargar_publicado
from exportar_pdf import exportar_pdf
from grilla import GrillaHorario
from usuarios_tab import PanelUsuarios


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class Aplicacion(tb.Window):

    def __init__(self, usuario, repo):
        super().__init__(
            title="Distribución de Horarios — Ing. en Software (ULEAM)",
            themename="cosmo",
            size=(1180, 720),
            resizable=(True, True),
        )
        self.minsize(1000, 620)

        self.usuario = usuario
        self.repo = repo
        self.cerrar_sesion = False

        self.niveles = construir_niveles()
        self.docentes = construir_docentes()
        self.aulas = construir_aulas()
        self.horario = None
        self.gen = None
        self.origen = ""
        self._filas = {}

        self._construir_barra_superior()
        self._construir_notebook()

        self.after(150, self._inicio)

    # -- construcción de la interfaz --------------------------------------

    def _construir_barra_superior(self):
        barra = tb.Frame(self, padding=(15, 12))
        barra.pack(fill=X)

        titulo = tb.Frame(barra)
        titulo.pack(side=LEFT)
        tb.Label(titulo, text="Distribución de Horarios",
                  font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tb.Label(titulo, text=f"Administrador · {self.usuario.nombre}",
                  bootstyle="secondary", font=("Segoe UI", 10)).pack(anchor="w")

        contenedor_derecha = tb.Frame(barra)
        contenedor_derecha.pack(side=RIGHT)

        tb.Button(contenedor_derecha, text="Cerrar sesión", bootstyle="secondary-outline",
                   command=self._cerrar_sesion).pack(side=RIGHT)

        self.lbl_estado = tb.Label(contenedor_derecha, text="Sin generar",
                                     bootstyle="secondary", font=("Segoe UI", 10))
        self.lbl_estado.pack(side=RIGHT, padx=(0, 15))

        tb.Button(contenedor_derecha, text="⟳  Generar horario",
                   bootstyle="success", command=self._generar).pack(side=RIGHT)
        tb.Button(contenedor_derecha, text="Exportar PDF", bootstyle="danger",
                   command=self._exportar_pdf).pack(side=RIGHT, padx=(0, 8))
        tb.Button(contenedor_derecha, text="Guardar", bootstyle="primary",
                   command=self._guardar_archivo).pack(side=RIGHT, padx=(0, 8))
        tb.Button(contenedor_derecha, text="Abrir", bootstyle="primary-outline",
                   command=self._abrir_archivo).pack(side=RIGHT, padx=(0, 8))

    def _construir_notebook(self):
        self.notebook = tb.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=15, pady=(0, 15))

        self.tab_nivel = tb.Frame(self.notebook, padding=12)
        self.tab_docente = tb.Frame(self.notebook, padding=12)
        self.tab_aula = tb.Frame(self.notebook, padding=12)
        self.tab_editar = tb.Frame(self.notebook, padding=12)
        self.tab_resumen = tb.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_nivel, text="  Por Nivel  ")
        self.notebook.add(self.tab_docente, text="  Por Docente  ")
        self.notebook.add(self.tab_aula, text="  Por Aula  ")
        self.notebook.add(self.tab_editar, text="  Editar  ")
        self.notebook.add(self.tab_resumen, text="  Resumen  ")
        self.panel_usuarios = PanelUsuarios(
            self.notebook, self.repo, self.docentes, self.niveles, self.usuario)
        self.notebook.add(self.panel_usuarios, text="  Usuarios  ")

        self._construir_tab_nivel()
        self._construir_tab_docente()
        self._construir_tab_aula()
        self._construir_tab_editar()
        self._construir_tab_resumen()

    def _fila_seleccion(self, padre, texto, valores, ancho):
        fila = tb.Frame(padre)
        fila.pack(fill=X, pady=(0, 10))
        tb.Label(fila, text=texto, font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 8))
        combo = tb.Combobox(fila, values=valores, state="readonly", width=ancho)
        combo.current(0)
        combo.pack(side=LEFT)
        return combo

    def _construir_tab_nivel(self):
        self.combo_nivel = self._fila_seleccion(
            self.tab_nivel, "Nivel:",
            [f"Nivel {n.numero}" for n in self.niveles], 15)
        self.combo_nivel.bind("<<ComboboxSelected>>", lambda e: self._refrescar_nivel())

        self.grilla_nivel = GrillaHorario(self.tab_nivel)
        self.grilla_nivel.pack(fill=BOTH, expand=True)

    def _construir_tab_docente(self):
        self.combo_docente = self._fila_seleccion(
            self.tab_docente, "Docente:",
            [d.nombre for d in self.docentes], 30)
        self.combo_docente.bind("<<ComboboxSelected>>", lambda e: self._refrescar_docente())

        self.grilla_docente = GrillaHorario(self.tab_docente)
        self.grilla_docente.pack(fill=BOTH, expand=True)

    def _construir_tab_aula(self):
        self.combo_aula = self._fila_seleccion(
            self.tab_aula, "Aula:",
            [a.nombre for a in self.aulas], 20)
        self.combo_aula.bind("<<ComboboxSelected>>", lambda e: self._refrescar_aula())

        self.grilla_aula = GrillaHorario(self.tab_aula)
        self.grilla_aula.pack(fill=BOTH, expand=True)

    def _construir_tab_editar(self):
        fila = tb.Frame(self.tab_editar)
        fila.pack(fill=X, pady=(0, 10))
        tb.Label(fila, text="Filtrar:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 8))
        self.combo_filtro = tb.Combobox(
            fila, values=["Todos"] + [f"Nivel {n.numero}" for n in self.niveles],
            state="readonly", width=15)
        self.combo_filtro.current(0)
        self.combo_filtro.pack(side=LEFT)
        self.combo_filtro.bind("<<ComboboxSelected>>", lambda e: self._refrescar_editar())
        tb.Button(fila, text="Editar seleccionada", bootstyle="warning",
                  command=self._editar_seleccionada).pack(side=RIGHT)

        contenedor = tb.Frame(self.tab_editar)
        contenedor.pack(fill=BOTH, expand=True)

        columnas = ("nivel", "materia", "sesion", "dia", "hora", "docente", "aula")
        titulos = ("Nivel", "Materia", "Sesión", "Día", "Hora", "Docente", "Aula")
        anchos = (60, 280, 70, 90, 110, 180, 120)
        self.tree = tb.Treeview(contenedor, columns=columnas, show="headings",
                                 bootstyle="primary", selectmode="browse")
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=ancho, anchor="w")
        scroll = tb.Scrollbar(contenedor, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)
        self.tree.bind("<Double-1>", lambda e: self._editar_seleccionada())

    def _construir_tab_resumen(self):
        self.txt_resumen = tk.Text(self.tab_resumen, wrap="word", font=("Consolas", 10),
                                    relief="flat", borderwidth=0)
        self.txt_resumen.pack(fill=BOTH, expand=True)
        self.txt_resumen.insert("1.0", "Presiona «Generar horario» para crear una distribución.")
        self.txt_resumen.configure(state="disabled")

    # -- lógica -------------------------------------------------------------

    def _generar(self):
        self.lbl_estado.configure(text="Generando…", bootstyle="warning")
        self.update_idletasks()

        gen = GeneradorHorarios(self.niveles, self.docentes, self.aulas)
        try:
            self.horario = gen.generar(optimizar=True)
        except SinSolucionError as e:
            self.lbl_estado.configure(text="Sin solución", bootstyle="danger")
            Messagebox.show_error(str(e), "No se pudo generar el horario")
            return

        self.gen = gen
        self.origen = "Generado automáticamente"
        self.lbl_estado.configure(
            text=f"Generado en {gen.tiempo_generacion:.2f} s", bootstyle="success")
        self._refrescar_todo()
        self._publicar()

    def _inicio(self):
        try:
            horario = cargar_publicado(self.niveles, self.docentes, self.aulas)
        except (ValueError, KeyError, OSError):
            horario = None
        if horario is None:
            self._generar()
            return
        self.horario = horario
        self.origen = "Horario publicado"
        self.lbl_estado.configure(text="Horario publicado cargado", bootstyle="success")
        self._refrescar_todo()

    def _publicar(self):
        try:
            publicar(self.horario)
        except OSError as e:
            Messagebox.show_warning(
                f"No se pudo publicar el horario para docentes y estudiantes.\n{e}", "Publicación")

    def _cerrar_sesion(self):
        self.cerrar_sesion = True
        self.destroy()

    def _refrescar_todo(self):
        self._refrescar_nivel()
        self._refrescar_docente()
        self._refrescar_aula()
        self._refrescar_editar()
        self._refrescar_resumen()

    def _guardar_archivo(self):
        if self.horario is None:
            Messagebox.show_warning("Primero genera o abre un horario.", "Sin horario")
            return
        ruta = filedialog.asksaveasfilename(
            title="Guardar horario", defaultextension=".json",
            initialfile="horario_uleam.json", filetypes=[("Horario (JSON)", "*.json")])
        if not ruta:
            return
        try:
            guardar_json(ruta, self.horario)
        except OSError as e:
            Messagebox.show_error(f"No se pudo guardar el archivo.\n{e}", "Error al guardar")
            return
        self.lbl_estado.configure(text="Horario guardado", bootstyle="success")

    def _abrir_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Abrir horario", filetypes=[("Horario (JSON)", "*.json")])
        if not ruta:
            return
        try:
            horario = cargar_json(ruta, self.niveles, self.docentes, self.aulas)
        except (ValueError, KeyError, OSError) as e:
            Messagebox.show_error(f"No se pudo abrir el archivo.\n{e}", "Error al abrir")
            return
        self.horario = horario
        self.gen = None
        self.origen = "Cargado desde archivo"
        self.lbl_estado.configure(text="Horario cargado", bootstyle="success")
        self._refrescar_todo()
        self._publicar()

    def _exportar_pdf(self):
        if self.horario is None:
            Messagebox.show_warning("Primero genera o abre un horario.", "Sin horario")
            return
        ruta = filedialog.asksaveasfilename(
            title="Exportar PDF", defaultextension=".pdf",
            initialfile="horario_uleam.pdf", filetypes=[("PDF", "*.pdf")])
        if not ruta:
            return
        try:
            exportar_pdf(ruta, self.horario, self.niveles, self.docentes, self.aulas)
        except OSError as e:
            Messagebox.show_error(
                f"No se pudo guardar el PDF (¿está abierto en otro programa?).\n{e}",
                "Error al exportar")
            return
        self.lbl_estado.configure(text="PDF exportado", bootstyle="success")
        if hasattr(os, "startfile"):
            os.startfile(ruta)

    def _editar_seleccionada(self):
        if self.horario is None:
            return
        seleccion = self.tree.selection()
        if not seleccion:
            Messagebox.show_warning("Selecciona una sesión de la tabla.", "Editar")
            return
        asignacion = self._filas[seleccion[0]]
        if editar_asignacion(self, self.horario, asignacion, self.docentes, self.aulas):
            if "ediciones" not in self.origen:
                self.origen += " + ediciones manuales"
            self.lbl_estado.configure(text="Horario editado", bootstyle="info")
            self._refrescar_todo()
            self._publicar()

    def _refrescar_editar(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._filas = {}
        if self.horario is None:
            return
        asigs = self.horario.asignaciones
        indice = self.combo_filtro.current()
        if indice > 0:
            numero = self.niveles[indice - 1].numero
            asigs = [a for a in asigs if a.sesion.nivel.numero == numero]
        asigs = sorted(asigs, key=lambda a: (a.sesion.nivel.numero, a.sesion.materia.codigo, a.sesion.indice))
        for i, a in enumerate(asigs):
            iid = str(i)
            self._filas[iid] = a
            hora = f"{hora_inicio(a.bloque_inicio)} - {hora_fin(a.bloque_inicio + a.sesion.duracion - 1)}"
            self.tree.insert("", "end", iid=iid, values=(
                a.sesion.nivel.numero, a.sesion.materia.nombre, a.sesion.indice,
                DIAS[a.dia], hora, a.docente.nombre, a.aula.nombre))

    def _refrescar_nivel(self):
        if self.horario is None:
            return
        numero = self.niveles[self.combo_nivel.current()].numero
        asigs = self.horario.por_nivel(numero)
        self.grilla_nivel.mostrar(asigs, etiqueta_extra=lambda a: a.docente.nombre)

    def _refrescar_docente(self):
        if self.horario is None:
            return
        docente = self.docentes[self.combo_docente.current()]
        asigs = self.horario.por_docente(docente.id)
        self.grilla_docente.mostrar(asigs, etiqueta_extra=lambda a: f"Nivel {a.sesion.nivel.numero}")

    def _refrescar_aula(self):
        if self.horario is None:
            return
        aula = self.aulas[self.combo_aula.current()]
        asigs = self.horario.por_aula(aula.id)
        self.grilla_aula.mostrar(asigs, etiqueta_extra=lambda a: f"Nivel {a.sesion.nivel.numero}")

    def _refrescar_resumen(self):
        total_horas = sum(a.sesion.duracion for a in self.horario.asignaciones)
        texto = (
            "RESUMEN DEL HORARIO\n"
            + "-" * 42 + "\n"
            f"Origen                   : {self.origen}\n"
            f"Sesiones asignadas       : {len(self.horario.asignaciones)}\n"
            f"Horas semanales totales  : {total_horas}\n"
            f"Niveles                  : {len(self.niveles)}\n"
            f"Docentes                 : {len(self.docentes)}\n"
            f"Aulas                    : {len(self.aulas)}\n"
        )
        if self.gen is not None:
            texto += (
                f"Tiempo de generación     : {self.gen.tiempo_generacion:.3f} s\n"
                f"Retrocesos (backtracks)  : {self.gen.backtracks}\n"
                f"Pasos explorados         : {self.gen._pasos}\n"
            )
        texto += "\nCosto de restricciones blandas (menor es mejor)\n"
        for r in RESTRICCIONES_BLANDAS:
            texto += f"{type(r).__name__:<25}: {r.costo(self.horario)}\n"
        texto += "\nLeyenda: celdas naranjas = requieren laboratorio · celdas azules = aula normal.\n"

        self.txt_resumen.configure(state="normal")
        self.txt_resumen.delete("1.0", "end")
        self.txt_resumen.insert("1.0", texto)
        self.txt_resumen.configure(state="disabled")
