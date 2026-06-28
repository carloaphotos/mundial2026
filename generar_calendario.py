#!/usr/bin/env python3
"""Genera mundial.ics a partir de datos/partidos_2026.json.

No edites mundial.ics a mano: edita los datos y vuelve a ejecutar este archivo.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos" / "partidos_2026.json"
SALIDA = RAIZ / "mundial.ics"

MESES = (
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
DIAS = (
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo",
)


def escapar_texto(valor: str) -> str:
    """Escapa texto RFC 5545 sin convertir los saltos en texto visible."""
    return (
        valor.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\r\n", "\n")
        .replace("\n", r"\n")
    )


def doblar_linea(linea: str) -> list[str]:
    """Dobla líneas a 75 octetos sin partir caracteres UTF-8."""
    limite_inicial = 75
    limite_continuacion = 74
    partes: list[str] = []
    actual = ""
    limite = limite_inicial

    for caracter in linea:
        candidato = actual + caracter
        if actual and len(candidato.encode("utf-8")) > limite:
            partes.append(actual)
            actual = caracter
            limite = limite_continuacion
        else:
            actual = candidato
    partes.append(actual or "")

    return [partes[0]] + [" " + parte for parte in partes[1:]]


def fecha_bonita(fecha: datetime) -> str:
    return f"{DIAS[fecha.weekday()].capitalize()} {fecha.day} de {MESES[fecha.month]} de {fecha.year}"


def resumen(partido: dict) -> str:
    marca_mexico = partido["equipo_local"] == "México" or partido["equipo_visitante"] == "México"
    estrella = "⭐" if marca_mexico else ""
    return (
        f"{estrella}{partido['bandera_local']} {partido['equipo_local']} vs "
        f"{partido['equipo_visitante']} {partido['bandera_visitante']}"
    )


def texto_siguiente(partido: dict) -> str:
    if partido["numero"] == 104:
        return "➡️ El ganador será campeón del mundo."
    if partido["numero"] == 103:
        return "➡️ Partido por el tercer lugar."
    if "perdedor_siguiente_partido" in partido:
        return (
            f"➡️ El ganador enfrentará al ganador de la otra semifinal en la final "
            f"(partido {partido['siguiente_partido']}).\n"
            f"➡️ El perdedor jugará el partido por el tercer lugar "
            f"(partido {partido['perdedor_siguiente_partido']})."
        )
    return (
        f"➡️ El ganador enfrentará al ganador del partido "
        f"{partido['siguiente_partido']}."
    )


def descripcion(partido: dict, inicio: datetime, fin: datetime) -> str:
    return "\n".join((
        f"🏆 {partido['fase']}",
        f"📅 {fecha_bonita(inicio)}",
        f"🕐 {inicio:%H:%M}–{fin:%H:%M} (CDMX)",
        f"🏟️ {partido['estadio']}",
        f"📍 {partido['ciudad']}, {partido['pais']}",
        texto_siguiente(partido),
    ))


def propiedad(nombre: str, valor: str) -> list[str]:
    return doblar_linea(f"{nombre}:{valor}")


def cargar_datos() -> dict:
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    for campo in ("creado_en", "actualizado_en"):
        try:
            datetime.strptime(datos[campo], "%Y%m%dT%H%M%SZ")
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{campo} debe tener formato AAAAMMDDTHHMMSSZ") from exc
    return datos


def generar() -> str:
    datos = cargar_datos()
    lineas: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Calendario Mundial 2026//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Copa Mundial 2026",
        "X-WR-CALDESC:Partidos de eliminación directa en horario de Ciudad de México",
        "X-WR-TIMEZONE:America/Mexico_City",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
        "BEGIN:VTIMEZONE",
        "TZID:America/Mexico_City",
        "X-LIC-LOCATION:America/Mexico_City",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:-0600",
        "TZOFFSETTO:-0600",
        "TZNAME:UTC-06:00",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for partido in datos["partidos"]:
        inicio = datetime.strptime(
            f"{partido['fecha']} {partido['hora']}", "%Y-%m-%d %H:%M"
        )
        fin = inicio + timedelta(minutes=datos["duracion_minutos"])
        ubicacion = f"{partido['estadio']}, {partido['ciudad']}, {partido['pais']}"

        lineas.extend((
            "BEGIN:VEVENT",
            f"UID:mundial-2026-partido-{partido['numero']:03d}@calendario-mundial",
            f"DTSTAMP:{datos['creado_en']}",
            f"LAST-MODIFIED:{datos['actualizado_en']}",
            f"SEQUENCE:{partido.get('revision', 0)}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            f"DTSTART;TZID=America/Mexico_City:{inicio:%Y%m%dT%H%M%S}",
            f"DTEND;TZID=America/Mexico_City:{fin:%Y%m%dT%H%M%S}",
            f"SUMMARY:{escapar_texto(resumen(partido))}",
            f"DESCRIPTION:{escapar_texto(descripcion(partido, inicio, fin))}",
            f"LOCATION:{escapar_texto(ubicacion)}",
            f"CATEGORIES:Copa Mundial 2026,{escapar_texto(partido['fase'])}",
            "BEGIN:VALARM",
            "TRIGGER:-PT30M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Recordatorio del partido",
            "END:VALARM",
            "END:VEVENT",
        ))

    lineas.append("END:VCALENDAR")

    dobladas: list[str] = []
    for linea in lineas:
        dobladas.extend(doblar_linea(linea))
    return "\r\n".join(dobladas) + "\r\n"


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument(
        "--actualizar-marca",
        action="store_true",
        help="Actualiza actualizado_en antes de generar el calendario.",
    )
    opcion = argumentos.parse_args()

    if opcion.actualizar_marca:
        datos_actualizados = cargar_datos()
        datos_actualizados["actualizado_en"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        DATOS.write_text(
            json.dumps(datos_actualizados, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    SALIDA.write_bytes(generar().encode("utf-8"))
    print(f"Generado: {SALIDA}")
