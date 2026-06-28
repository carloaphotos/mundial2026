#!/usr/bin/env python3
"""
Validación básica del archivo mundial.ics.

Formato actual de las notas:
- Conserva fase, estadio, ciudad/país y siguiente cruce.
- No incluye fecha ni hora: esas ya las muestra la app de calendario.
"""

from __future__ import annotations

from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent
ICS = RAIZ / "mundial.ics"

ERRORES: list[str] = []


def comprobar(condicion: bool, mensaje: str) -> None:
    if not condicion:
        ERRORES.append(mensaje)


def main() -> int:
    if not ICS.exists():
        print("✗ No existe mundial.ics")
        return 1

    texto = ICS.read_text(encoding="utf-8")

    comprobar("BEGIN:VCALENDAR" in texto, "Falta BEGIN:VCALENDAR.")
    comprobar("END:VCALENDAR" in texto, "Falta END:VCALENDAR.")
    comprobar("BEGIN:VEVENT" in texto, "No hay eventos.")
    comprobar("TZID=America/Mexico_City" in texto, "Falta la zona horaria America/Mexico_City.")
    comprobar("BEGIN:VALARM" in texto, "Faltan recordatorios.")
    comprobar("TRIGGER:-PT30M" in texto, "El recordatorio no es de 30 minutos.")

    eventos = texto.split("BEGIN:VEVENT")[1:]
    comprobar(len(eventos) > 0, "No se encontraron eventos válidos.")

    for numero, bloque in enumerate(eventos, start=1):
        comprobar("SUMMARY:" in bloque, f"Evento {numero}: falta SUMMARY.")
        comprobar("DTSTART" in bloque, f"Evento {numero}: falta DTSTART.")
        comprobar("DTEND" in bloque, f"Evento {numero}: falta DTEND.")
        comprobar("LOCATION:" in bloque, f"Evento {numero}: falta LOCATION.")
        comprobar("DESCRIPTION:" in bloque, f"Evento {numero}: falta DESCRIPTION.")
        comprobar("🕒" not in bloque, f"Evento {numero}: la descripción aún incluye 🕒.")
        comprobar("📅" not in bloque, f"Evento {numero}: la descripción aún incluye 📅.")

    if ERRORES:
        print("El calendario tiene errores:")
        for error in ERRORES:
            print(f"✗ {error}")
        return 1

    print(f"✓ Calendario válido: {len(eventos)} eventos revisados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
