from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import DIAS, TOTAL_BLOQUES_DIA, hora_fin, hora_inicio

COLOR_LAB = "#fdebd0"
COLOR_NORMAL = "#d6eaf8"


def _grilla(asignaciones, extra):
    estilo_celda = ParagraphStyle("celda", fontName="Helvetica", fontSize=7.5, leading=9, alignment=1)
    datos = [["Hora"] + DIAS]
    for b in range(TOTAL_BLOQUES_DIA):
        datos.append([f"{hora_inicio(b)}-{hora_fin(b)}"] + [""] * len(DIAS))

    estilos = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    for a in asignaciones:
        fila = a.bloque_inicio + 1
        col = a.dia + 1
        ultima = fila + a.sesion.duracion - 1
        texto = (f"<b>{escape(a.sesion.materia.codigo)}</b><br/>"
                 f"{escape(extra(a))}<br/>{escape(a.aula.nombre)}")
        datos[fila][col] = Paragraph(texto, estilo_celda)
        color = COLOR_LAB if a.sesion.materia.requiere_laboratorio else COLOR_NORMAL
        estilos.append(("BACKGROUND", (col, fila), (col, ultima), colors.HexColor(color)))
        if ultima > fila:
            estilos.append(("SPAN", (col, fila), (col, ultima)))

    tabla = Table(datos, colWidths=[2.4 * cm] + [4.6 * cm] * len(DIAS),
                  rowHeights=[0.7 * cm] + [1.1 * cm] * TOTAL_BLOQUES_DIA)
    tabla.setStyle(TableStyle(estilos))
    return tabla


def _docente_de(a):
    return a.docente.nombre


def _nivel_de(a):
    return f"Nivel {a.sesion.nivel.numero}"


def exportar_pdf(ruta, horario, niveles, docentes, aulas):
    estilos = getSampleStyleSheet()
    estilo_nota = ParagraphStyle("nota", parent=estilos["Normal"], fontSize=7, leading=9)

    secciones = []
    for n in niveles:
        asigs = horario.por_nivel(n.numero)
        materias = "; ".join(f"{m.codigo} {m.nombre}" for m in n.materias)
        secciones.append((f"Horario por nivel — Nivel {n.numero}", asigs, _docente_de, materias))
    for d in docentes:
        secciones.append((f"Horario por docente — {d.nombre}", horario.por_docente(d.id), _nivel_de, ""))
    for au in aulas:
        secciones.append((f"Horario por aula — {au.nombre}", horario.por_aula(au.id), _nivel_de, ""))

    historia = []
    for i, (titulo, asigs, extra, materias) in enumerate(secciones):
        if i:
            historia.append(PageBreak())
        horas = sum(a.sesion.duracion for a in asigs)
        historia.append(Paragraph(f"{escape(titulo)} ({horas} h/semana)", estilos["Heading2"]))
        historia.append(_grilla(asigs, extra))
        historia.append(Spacer(1, 0.2 * cm))
        historia.append(Paragraph(
            "Naranja: requiere laboratorio · Azul: aula normal", estilo_nota))
        if materias:
            historia.append(Paragraph(escape(materias), estilo_nota))

    doc = SimpleDocTemplate(
        ruta, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        title="Horarios — Ingeniería en Software (ULEAM)",
    )
    doc.build(historia)
