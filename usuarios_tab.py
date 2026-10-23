from tkinter import messagebox, simpledialog

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, X, Y, LEFT, RIGHT
from ttkbootstrap.dialogs import Messagebox

from auth import ROLES, ADMIN, DOCENTE, ESTUDIANTE


class PanelUsuarios(tb.Frame):

    def __init__(self, master, repo, docentes, niveles, usuario_actual):
        super().__init__(master, padding=12)
        self.repo = repo
        self.docentes = docentes
        self.niveles = niveles
        self.usuario_actual = usuario_actual

        form = tb.Labelframe(self, text="Nuevo usuario", padding=12)
        form.pack(fill=X, pady=(0, 12))

        self.ent_usuario = tb.Entry(form, width=24)
        self.ent_nombre = tb.Entry(form, width=30)
        self.combo_rol = tb.Combobox(form, values=[r.capitalize() for r in ROLES],
                                     state="readonly", width=22)
        self.combo_ref = tb.Combobox(form, values=[], state="disabled", width=28)
        self.ent_clave = tb.Entry(form, show="•", width=24)

        self._fila(form, 0, "Usuario:", self.ent_usuario, "Nombre:", self.ent_nombre)
        self._fila(form, 1, "Rol:", self.combo_rol, "Vinculado a:", self.combo_ref)
        self._fila(form, 2, "Contraseña:", self.ent_clave, None, None)
        tb.Button(form, text="Crear usuario", bootstyle="success",
                  command=self._crear).grid(row=2, column=3, sticky="e", pady=4)

        self.combo_rol.current(ROLES.index(ESTUDIANTE))
        self.combo_rol.bind("<<ComboboxSelected>>", self._al_cambiar_rol)
        self._al_cambiar_rol()

        acciones = tb.Frame(self)
        acciones.pack(fill=X, pady=(0, 8))
        tb.Label(acciones, text="Usuarios registrados", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        tb.Button(acciones, text="Eliminar usuario", bootstyle="danger-outline",
                  command=self._eliminar).pack(side=RIGHT)
        tb.Button(acciones, text="Restablecer contraseña", bootstyle="warning-outline",
                  command=self._restablecer).pack(side=RIGHT, padx=(0, 8))

        contenedor = tb.Frame(self)
        contenedor.pack(fill=BOTH, expand=True)
        columnas = ("usuario", "nombre", "rol", "vinculo")
        self.tree = tb.Treeview(contenedor, columns=columnas, show="headings",
                                bootstyle="primary", selectmode="browse")
        for col, titulo, ancho in zip(columnas, ("Usuario", "Nombre", "Rol", "Vinculado a"),
                                      (140, 260, 120, 200)):
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=ancho, anchor="w")
        scroll = tb.Scrollbar(contenedor, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        self._refrescar()

    def _fila(self, form, fila, texto1, widget1, texto2, widget2):
        tb.Label(form, text=texto1, font=("Segoe UI", 10, "bold")).grid(
            row=fila, column=0, sticky="w", padx=(0, 8), pady=4)
        widget1.grid(row=fila, column=1, sticky="w", padx=(0, 24), pady=4)
        if texto2:
            tb.Label(form, text=texto2, font=("Segoe UI", 10, "bold")).grid(
                row=fila, column=2, sticky="w", padx=(0, 8), pady=4)
            widget2.grid(row=fila, column=3, sticky="w", pady=4)

    def _al_cambiar_rol(self, _evento=None):
        rol = ROLES[self.combo_rol.current()]
        if rol == DOCENTE:
            valores = [d.nombre for d in self.docentes]
        elif rol == ESTUDIANTE:
            valores = [f"Nivel {n.numero}" for n in self.niveles]
        else:
            valores = []
        self.combo_ref.configure(values=valores, state="readonly" if valores else "disabled")
        self.combo_ref.set("")
        if valores:
            self.combo_ref.current(0)

    def _vinculo(self, u):
        if u.rol == DOCENTE:
            return next((d.nombre for d in self.docentes if d.id == u.referencia), u.referencia)
        if u.rol == ESTUDIANTE:
            return f"Nivel {u.referencia}"
        return "—"

    def _refrescar(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for u in self.repo.todos():
            self.tree.insert("", "end", iid=u.usuario,
                             values=(u.usuario, u.nombre, u.rol.capitalize(), self._vinculo(u)))

    def _seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            Messagebox.show_warning("Selecciona un usuario de la tabla.", "Usuarios")
            return None
        return seleccion[0]

    def _crear(self):
        rol = ROLES[self.combo_rol.current()]
        indice = self.combo_ref.current()
        referencia = ""
        if rol == DOCENTE and indice >= 0:
            referencia = self.docentes[indice].id
        elif rol == ESTUDIANTE and indice >= 0:
            referencia = str(self.niveles[indice].numero)
        try:
            self.repo.crear(self.ent_usuario.get(), self.ent_nombre.get(), rol,
                            referencia, self.ent_clave.get())
        except ValueError as e:
            Messagebox.show_error(str(e), "No se pudo crear el usuario")
            return
        for entrada in (self.ent_usuario, self.ent_nombre, self.ent_clave):
            entrada.delete(0, "end")
        self._refrescar()

    def _eliminar(self):
        usuario = self._seleccionado()
        if usuario is None:
            return
        if usuario == self.usuario_actual.usuario:
            Messagebox.show_error("No puedes eliminar tu propia cuenta.", "Usuarios")
            return
        if not messagebox.askyesno("Eliminar usuario", f"¿Eliminar al usuario «{usuario}»?"):
            return
        try:
            self.repo.eliminar(usuario)
        except ValueError as e:
            Messagebox.show_error(str(e), "No se pudo eliminar")
            return
        self._refrescar()

    def _restablecer(self):
        usuario = self._seleccionado()
        if usuario is None:
            return
        nueva = simpledialog.askstring(
            "Restablecer contraseña", f"Nueva contraseña para «{usuario}»:", show="•", parent=self)
        if nueva is None:
            return
        try:
            self.repo.cambiar_clave(usuario, nueva)
        except ValueError as e:
            Messagebox.show_error(str(e), "No se pudo cambiar la contraseña")
            return
        Messagebox.show_info("Contraseña actualizada.", "Usuarios")
