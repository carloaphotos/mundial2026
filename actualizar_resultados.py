#!/usr/bin/env python3
"""Actualiza automáticamente el calendario del Mundial 2026 desde ESPN.

No requiere API key ni servicios de pago.
Consulta el marcador público de ESPN, conserva siempre los nombres en español
y propaga ganadores/perdedores a los siguientes cruces.

Nota: ESPN no publica este endpoint como una API contractual; por eso este
proyecto mantiene una tabla propia de nombres en español y nunca publica
texto no validado en el calendario.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos" / "partidos_2026.json"
CDMX = ZoneInfo("America/Mexico_City")

# Todos los partidos del torneo; limit=200 cubre los 104 encuentros.
ESPN_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/"
    "scoreboard?limit=200&dates=20260611-20260719"
)

INICIO_TORNEO = datetime(2026, 6, 28, tzinfo=CDMX).date()
FIN_TORNEO = datetime(2026, 7, 19, tzinfo=CDMX).date()
BANDERA_INGLATERRA = "🏴"

# Esta lista evita que un nombre en inglés llegue al .ics público.
INGLES_A_ESPANOL: dict[str, tuple[str, str]] = {
    "South Africa": ("Sudáfrica", "🇿🇦"),
    "Canada": ("Canadá", "🇨🇦"),
    "Germany": ("Alemania", "🇩🇪"),
    "Paraguay": ("Paraguay", "🇵🇾"),
    "Netherlands": ("Países Bajos", "🇳🇱"),
    "Morocco": ("Marruecos", "🇲🇦"),
    "Brazil": ("Brasil", "🇧🇷"),
    "Japan": ("Japón", "🇯🇵"),
    "France": ("Francia", "🇫🇷"),
    "Sweden": ("Suecia", "🇸🇪"),
    "Ivory Coast": ("Costa de Marfil", "🇨🇮"),
    "Cote d'Ivoire": ("Costa de Marfil", "🇨🇮"),
    "Côte d'Ivoire": ("Costa de Marfil", "🇨🇮"),
    "Norway": ("Noruega", "🇳🇴"),
    "Mexico": ("México", "🇲🇽"),
    "Ecuador": ("Ecuador", "🇪🇨"),
    "England": ("Inglaterra", BANDERA_INGLATERRA),
    "DR Congo": ("RD Congo", "🇨🇩"),
    "Congo DR": ("RD Congo", "🇨🇩"),
    "Democratic Republic of the Congo": ("RD Congo", "🇨🇩"),
    "United States": ("Estados Unidos", "🇺🇸"),
    "USA": ("Estados Unidos", "🇺🇸"),
    "Bosnia and Herzegovina": ("Bosnia y Herzegovina", "🇧🇦"),
    "Bosnia-Herzegovina": ("Bosnia y Herzegovina", "🇧🇦"),
    "Belgium": ("Bélgica", "🇧🇪"),
    "Senegal": ("Senegal", "🇸🇳"),
    "Portugal": ("Portugal", "🇵🇹"),
    "Croatia": ("Croacia", "🇭🇷"),
    "Spain": ("España", "🇪🇸"),
    "Austria": ("Austria", "🇦🇹"),
    "Switzerland": ("Suiza", "🇨🇭"),
    "Algeria": ("Argelia", "🇩🇿"),
    "Argentina": ("Argentina", "🇦🇷"),
    "Cape Verde": ("Cabo Verde", "🇨🇻"),
    "Cabo Verde": ("Cabo Verde", "🇨🇻"),
    "Colombia": ("Colombia", "🇨🇴"),
    "Ghana": ("Ghana", "🇬🇭"),
    "Australia": ("Australia", "🇦🇺"),
    "Egypt": ("Egipto", "🇪🇬"),
}

# resultado que viaja, partido de destino, lado de destino
DESTINOS: dict[int, list[tuple[str, int, str]]] = {
    73: [("ganador", 90, "local")],
    74: [("ganador", 89, "local")],
    75: [("ganador", 90, "visitante")],
    76: [("ganador", 91, "local")],
    77: [("ganador", 89, "visitante")],
    78: [("ganador", 91, "visitante")],
    79: [("ganador", 92, "local")],
    80: [("ganador", 92, "visitante")],
    81: [("ganador", 94, "local")],
    82: [("ganador", 94, "visitante")],
    83: [("ganador", 93, "local")],
    84: [("ganador", 93, "visitante")],
    85: [("ganador", 96, "local")],
    86: [("ganador", 95, "local")],
    87: [("ganador", 96, "visitante")],
    88: [("ganador", 95, "visitante")],
    89: [("ganador", 97, "local")],
    90: [("ganador", 97, "visitante")],
    91: [("ganador", 99, "local")],
    92: [("ganador", 99, "visitante")],
    93: [("ganador", 98, "local")],
    94: [("ganador", 98, "visitante")],
    95: [("ganador", 100, "local")],
    96: [("ganador", 100, "visitante")],
    97: [("ganador", 101, "local")],
    98: [("ganador", 101, "visitante")],
    99: [("ganador", 102, "local")],
    100: [("ganador", 102, "visitante")],
    101: [("ganador", 104, "local"), ("perdedor", 103, "local")],
    102: [("ganador", 104, "visitante"), ("perdedor", 103, "visitante")],
}


def cargar_datos() -> dict[str, Any]:
    return json.loads(DATOS.read_text(encoding="utf-8"))


def guardar_datos(datos: dict[str, Any]) -> None:
    DATOS.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ahora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def nombre_crudo(competidor: dict[str, Any]) -> str:
    equipo = competidor.get("team", {})
    return str(
        equipo.get("displayName")
        or equipo.get("name")
        or competidor.get("displayName")
        or ""
    ).strip()


def entero_o_nulo(valor: Any) -> int | None:
    try:
        return int(str(valor))
    except (TypeError, ValueError):
        return None


def equipo_en_espanol(nombre: str) -> tuple[str, str] | None:
    return INGLES_A_ESPANOL.get(nombre.strip())


def cargar_eventos_espn() -> list[dict[str, Any]]:
    solicitud = Request(
        ESPN_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "mundial2026-calendario/1.0",
        },
    )
    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            contenido = json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"ESPN respondió HTTP {exc.code}.") from exc
    except URLError as exc:
        raise RuntimeError("No fue posible contactar el marcador de ESPN.") from exc

    eventos = contenido.get("events")
    if not isinstance(eventos, list):
        raise RuntimeError("ESPN no devolvió una lista de partidos.")
    return eventos


def normalizar_evento(evento: dict[str, Any]) -> dict[str, Any] | None:
    competencias = evento.get("competitions", [])
    if not isinstance(competencias, list) or not competencias:
        return None
    competencia = competencias[0]

    competidores = competencia.get("competitors", [])
    if not isinstance(competidores, list):
        return None

    local = next((x for x in competidores if x.get("homeAway") == "home"), None)
    visitante = next((x for x in competidores if x.get("homeAway") == "away"), None)
    if not isinstance(local, dict) or not isinstance(visitante, dict):
        return None

    marca = str(competencia.get("date") or evento.get("date") or "")
    if marca.endswith("Z"):
        marca = marca[:-1] + "+00:00"
    try:
        inicio = datetime.fromisoformat(marca).astimezone(CDMX)
    except ValueError:
        return None

    estado = competencia.get("status") or evento.get("status") or {}
    tipo_estado = estado.get("type") if isinstance(estado, dict) else {}
    terminado = bool(isinstance(tipo_estado, dict) and tipo_estado.get("completed"))

    return {
        "id": str(evento.get("id") or ""),
        "fecha": inicio.strftime("%Y-%m-%d"),
        "hora": inicio.strftime("%H:%M"),
        "terminado": terminado,
        "local": nombre_crudo(local),
        "visitante": nombre_crudo(visitante),
        "ganador_local": local.get("winner") is True,
        "ganador_visitante": visitante.get("winner") is True,
        "marcador_local": entero_o_nulo(local.get("score")),
        "marcador_visitante": entero_o_nulo(visitante.get("score")),
    }


def cambiar(partido: dict[str, Any], campo: str, valor: Any, publico: bool = True) -> bool:
    if partido.get(campo) == valor:
        return False
    partido[campo] = valor
    if publico:
        partido["revision"] = int(partido.get("revision", 0)) + 1
    return True


def asignar_equipo(partido: dict[str, Any], lado: str, equipo: tuple[str, str]) -> bool:
    nombre, bandera = equipo
    cambio = False
    cambio |= cambiar(partido, f"equipo_{lado}", nombre)
    cambio |= cambiar(partido, f"bandera_{lado}", bandera)
    return cambio


def localizar_partido(
    evento: dict[str, Any],
    por_numero: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    # Un identificador guardado elimina cualquier ambigüedad en futuras consultas.
    for partido in por_numero.values():
        if str(partido.get("espn_event_id", "")) == evento["id"] and evento["id"]:
            return partido

    # En esta fase cada fecha y hora CDMX corresponde a un solo partido.
    candidatos = [
        partido
        for partido in por_numero.values()
        if partido.get("fecha") == evento["fecha"]
        and partido.get("hora") == evento["hora"]
    ]
    return candidatos[0] if len(candidatos) == 1 else None


def sincronizar(datos: dict[str, Any], eventos: list[dict[str, Any]]) -> tuple[bool, dict[str, int]]:
    partidos = datos.get("partidos", [])
    por_numero = {int(partido["numero"]): partido for partido in partidos}
    cambio_total = False
    resumen = {"asignados": 0, "finalizados": 0, "sin_asignar": 0}

    for bruto in eventos:
        evento = normalizar_evento(bruto)
        if evento is None:
            continue

        partido = localizar_partido(evento, por_numero)
        if partido is None:
            continue

        resumen["asignados"] += 1
        if evento["id"]:
            cambio_total |= cambiar(partido, "espn_event_id", evento["id"], publico=False)

        # ESPN puede confirmar participantes de cruces futuros antes del partido.
        local_es = equipo_en_espanol(evento["local"])
        visitante_es = equipo_en_espanol(evento["visitante"])
        if local_es and visitante_es:
            cambio_total |= asignar_equipo(partido, "local", local_es)
            cambio_total |= asignar_equipo(partido, "visitante", visitante_es)

        if not evento["terminado"]:
            continue

        ganador: tuple[str, str] | None = None
        perdedor: tuple[str, str] | None = None
        if evento["ganador_local"] and local_es and visitante_es:
            ganador, perdedor = local_es, visitante_es
        elif evento["ganador_visitante"] and local_es and visitante_es:
            ganador, perdedor = visitante_es, local_es
        else:
            # Un empate sin ganador explícito puede significar que ESPN aún
            # no terminó de publicar el desenlace de penales.
            print(f"Partido {partido['numero']}: finalizado, esperando ganador confirmado.")
            continue

        resumen["finalizados"] += 1
        resultado = {
            "estado": "Finalizado",
            "marcador_local": evento["marcador_local"],
            "marcador_visitante": evento["marcador_visitante"],
            "ganador": ganador[0],
        }
        cambio_total |= cambiar(partido, "resultado", resultado, publico=False)

        for tipo, destino_numero, lado in DESTINOS.get(int(partido["numero"]), []):
            destino = por_numero[destino_numero]
            equipo = ganador if tipo == "ganador" else perdedor
            cambio_total |= asignar_equipo(destino, lado, equipo)

    resumen["sin_asignar"] = max(0, len(eventos) - resumen["asignados"])
    return cambio_total, resumen


def main() -> int:
    hoy = datetime.now(CDMX).date()
    if not (INICIO_TORNEO <= hoy <= FIN_TORNEO):
        print("Fuera de la fase eliminatoria: no se consulta ESPN.")
        return 0

    datos = cargar_datos()
    eventos = cargar_eventos_espn()
    cambio, resumen = sincronizar(datos, eventos)

    if not cambio:
        print(
            "Sin cambios. "
            f"Partidos encontrados: {resumen['asignados']}; "
            f"finalizados: {resumen['finalizados']}."
        )
        return 0

    datos["actualizado_en"] = ahora_utc()
    guardar_datos(datos)
    print(
        "Datos actualizados. "
        f"Partidos encontrados: {resumen['asignados']}; "
        f"finalizados: {resumen['finalizados']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
