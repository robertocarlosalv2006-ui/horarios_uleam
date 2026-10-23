# Sistema de Distribución de Horarios — Ingeniería en Software (ULEAM)

Proyecto de POO que genera automáticamente el horario semanal de todas las
materias de la carrera de Ingeniería en Software, resolviendo el problema
como un **CSP (Constraint Satisfaction Problem)** con **backtracking hecho a
mano** (sin librerías externas de resolución de restricciones).

## Cómo ejecutar

```bash
pip install -r requirements.txt
python main.py
```

Al abrir aparece el inicio de sesión. El administrador genera, edita, guarda y
exporta el horario; cada cambio se publica automáticamente para que lo vean
docentes y estudiantes.

## Usuarios de ejemplo (se crean la primera vez)

| Rol | Usuario | Contraseña | Interfaz |
|---|---|---|---|
| Administrador | `admin` | `admin123` | Generar, editar, guardar, PDF, resumen y gestión de usuarios |
| Docente | `docente01` … `docente10` | `docente123` | Su horario semanal y sus materias |
| Estudiante | `estudiante1` … `estudiante8` | `estudiante123` | Horario de su nivel y sus materias |

Las contraseñas se guardan con PBKDF2 + sal en `datos/usuarios.json`. El
horario publicado vive en `datos/horario_publicado.json`. Borrar la carpeta
`datos` restablece usuarios y horario.

## Estructura del proyecto

| Archivo | Contenido |
|---|---|
| `models.py` | Clases de dominio: `Materia`, `Docente`, `Aula`, `Nivel`, `Sesion`, `Asignacion`, `Horario`. |
| `datos_ejemplo.py` | Datos de ejemplo: malla curricular real (pensum 2022), 10 docentes y 6 aulas. |
| `restricciones.py` | Restricciones duras (obligatorias) y blandas (preferencias), modeladas como clases con polimorfismo. |
| `solver.py` | Motor de backtracking: construcción de variables/dominios, MRV, forward checking y optimización local. |
| `gui.py` | Interfaz del administrador (ttkbootstrap): vistas por nivel/docente/aula, edición, guardar, PDF y usuarios. |
| `edicion.py` | Edición manual de sesiones con validación de restricciones duras. |
| `persistencia.py` | Guardar/abrir horarios en JSON y publicarlos. |
| `exportar_pdf.py` | Exportación del horario a PDF (reportlab). |
| `auth.py` | Usuarios, roles y contraseñas con hash. |
| `login.py` | Ventana de inicio de sesión. |
| `vistas.py` | Interfaces del docente y del estudiante. |
| `usuarios_tab.py` | Pestaña de gestión de usuarios (administrador). |
| `grilla.py` | Widget de grilla semanal reutilizable. |
| `rutas.py` | Rutas de la carpeta `datos`. |
| `main.py` | Punto de entrada: login y apertura de la interfaz según el rol. |

## El problema y cómo se resuelve

**Variables:** cada "sesión" de clase (una materia con 3h/semana, por
ejemplo, se reparte en sesiones de máximo 2h seguidas).

**Dominio de cada variable:** todas las combinaciones válidas de
`(día, hora de inicio, docente, aula)` que respetan las materias que el
docente puede dictar, su disponibilidad, y el tipo de aula requerido
(laboratorio o normal).

**Restricciones duras** (nunca se violan):
1. Un docente no dicta dos clases a la vez.
2. Un aula no aloja dos clases a la vez.
3. Un nivel no recibe dos materias a la vez.
4. Se respeta la disponibilidad declarada de cada docente.
5. Las materias que requieren laboratorio solo se ubican en aulas de
   laboratorio (y viceversa).

**Restricciones blandas** (se optimizan, no son obligatorias):
1. Minimizar huecos en el horario de cada nivel.
2. Balancear la carga horaria de cada docente entre los días de la semana.

**Algoritmo:**
1. *Backtracking* con heurística **MRV** (se asigna primero la sesión con
   menos opciones disponibles) y **forward checking** (al asignar una
   sesión, se eliminan de los dominios de las demás las opciones que ya
   quedarían en conflicto; si una rama falla, se deshace y se prueba otra).
2. El orden en que se prueban las opciones de cada sesión prioriza el día
   menos cargado para el nivel y el docente, para repartir las clases en la
   semana en vez de amontonarlas.
3. Una vez encontrada una solución factible, una fase de **optimización
   local** mueve sesiones a horas más tempranas del mismo día cuando eso
   reduce huecos, sin romper ninguna restricción dura.

## Datos de ejemplo (ajustables en `datos_ejemplo.py`)

- **Jornadas:** matutina 07h00–13h00 y vespertina 13h00–19h00 (12 bloques de
  1 hora por día, lunes a viernes). Un nivel puede tener materias en ambas
  jornadas.
- **8 niveles**, un paralelo cada uno, con las materias reales de la malla
  curricular (pensum 2022).
- **10 docentes**, cada uno habilitado para materias afines a su área; dos
  de ellos con restricciones de disponibilidad (uno solo dicta en la
  mañana, otro no dicta los viernes) para probar que el algoritmo las
  respeta.
- **6 aulas**: 4 normales + 2 laboratorios.

## Cómo adaptarlo a datos reales

Todo el contenido "de ejemplo" vive en `datos_ejemplo.py`. Para usar datos
reales de la facultad basta con reemplazar las listas de `_MALLA`,
`construir_docentes()` y `construir_aulas()` — el resto del sistema
(modelo, restricciones, solver e interfaz) no necesita cambios.
