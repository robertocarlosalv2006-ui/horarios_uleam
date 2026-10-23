import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, X


class VentanaLogin(tb.Window):

    def __init__(self, repo):
        super().__init__(title="Iniciar sesión — Horarios ULEAM", themename="cosmo",
                         size=(420, 440), resizable=(False, False))
        self.repo = repo
        self.usuario = None

        marco = tb.Frame(self, padding=32)
        marco.pack(fill=BOTH, expand=True)

        tb.Label(marco, text="Distribución de Horarios", font=("Segoe UI", 18, "bold")).pack()
        tb.Label(marco, text="Ingeniería en Software · ULEAM", bootstyle="secondary",
                 font=("Segoe UI", 10)).pack(pady=(0, 28))

        tb.Label(marco, text="Usuario", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=X)
        self.ent_usuario = tb.Entry(marco)
        self.ent_usuario.pack(fill=X, pady=(2, 14))

        tb.Label(marco, text="Contraseña", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=X)
        self.ent_clave = tb.Entry(marco, show="•")
        self.ent_clave.pack(fill=X, pady=(2, 8))

        self.lbl_error = tb.Label(marco, text="", bootstyle="danger", font=("Segoe UI", 9))
        self.lbl_error.pack(fill=X, pady=(0, 8))

        tb.Button(marco, text="Ingresar", bootstyle="success", command=self._ingresar).pack(fill=X)

        self.bind("<Return>", lambda e: self._ingresar())
        self.place_window_center()
        self.ent_usuario.focus_set()

    def _ingresar(self):
        usuario = self.repo.autenticar(self.ent_usuario.get(), self.ent_clave.get())
        if usuario is None:
            self.lbl_error.configure(text="Usuario o contraseña incorrectos.")
            self.ent_clave.delete(0, "end")
            self.ent_clave.focus_set()
            return
        self.usuario = usuario
        self.destroy()
