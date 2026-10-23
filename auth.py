import hashlib
import json
import os
import secrets
from dataclasses import dataclass, asdict

from rutas import RUTA_USUARIOS

ADMIN = "administrador"
DOCENTE = "docente"
ESTUDIANTE = "estudiante"
ROLES = (ADMIN, DOCENTE, ESTUDIANTE)

ITERACIONES = 120_000
CLAVE_MIN = 4


@dataclass
class Usuario:
    usuario: str
    nombre: str
    rol: str
    referencia: str
    salt: str
    clave_hash: str


def _hashear(clave, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(salt), ITERACIONES).hex()


def _validar_clave(clave):
    if len(clave) < CLAVE_MIN:
        raise ValueError(f"La contraseña debe tener al menos {CLAVE_MIN} caracteres.")


class RepositorioUsuarios:

    def __init__(self, docentes, niveles, ruta=RUTA_USUARIOS):
        self.ruta = ruta
        self._usuarios = {}
        if os.path.exists(ruta):
            try:
                self._cargar()
            except (ValueError, TypeError, KeyError, OSError):
                self._usuarios = {}
                self._sembrar(docentes, niveles)
        else:
            self._sembrar(docentes, niveles)

    def _cargar(self):
        with open(self.ruta, "r", encoding="utf-8") as f:
            for item in json.load(f):
                u = Usuario(**item)
                self._usuarios[u.usuario] = u

    def _guardar(self):
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump([asdict(u) for u in self._usuarios.values()], f, ensure_ascii=False, indent=2)

    def _sembrar(self, docentes, niveles):
        self.crear("admin", "Administrador", ADMIN, "", "admin123", guardar=False)
        for i, d in enumerate(docentes, start=1):
            self.crear(f"docente{i:02d}", d.nombre, DOCENTE, d.id, "docente123", guardar=False)
        for n in niveles:
            self.crear(f"estudiante{n.numero}", f"Estudiante Nivel {n.numero}", ESTUDIANTE,
                       str(n.numero), "estudiante123", guardar=False)
        self._guardar()

    def todos(self):
        return sorted(self._usuarios.values(), key=lambda u: (ROLES.index(u.rol), u.usuario))

    def autenticar(self, usuario, clave):
        u = self._usuarios.get(usuario.strip().lower())
        if u is None:
            _hashear(clave, "00" * 16)
            return None
        if secrets.compare_digest(_hashear(clave, u.salt), u.clave_hash):
            return u
        return None

    def crear(self, usuario, nombre, rol, referencia, clave, guardar=True):
        usuario = usuario.strip().lower()
        if not usuario:
            raise ValueError("El usuario no puede estar vacío.")
        if " " in usuario:
            raise ValueError("El usuario no puede tener espacios.")
        if usuario in self._usuarios:
            raise ValueError("Ese usuario ya existe.")
        if rol not in ROLES:
            raise ValueError("Rol no válido.")
        if rol != ADMIN and not referencia:
            raise ValueError("Selecciona a qué docente o nivel pertenece.")
        _validar_clave(clave)
        salt = secrets.token_hex(16)
        self._usuarios[usuario] = Usuario(
            usuario, nombre.strip() or usuario, rol, referencia, salt, _hashear(clave, salt))
        if guardar:
            self._guardar()

    def cambiar_clave(self, usuario, clave):
        u = self._usuarios[usuario]
        _validar_clave(clave)
        u.salt = secrets.token_hex(16)
        u.clave_hash = _hashear(clave, u.salt)
        self._guardar()

    def eliminar(self, usuario):
        u = self._usuarios.get(usuario)
        if u is None:
            return
        if u.rol == ADMIN and sum(1 for x in self._usuarios.values() if x.rol == ADMIN) == 1:
            raise ValueError("Debe existir al menos un administrador.")
        del self._usuarios[usuario]
        self._guardar()
