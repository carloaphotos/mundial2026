#!/usr/bin/env python3
"""Sincroniza resultados del Mundial 2026 y propaga clasificados al cuadro.

Este archivo se ejecuta desde GitHub Actions. Consulta API-Football, mantiene los
nombres en español, actualiza las banderas y envía automáticamente ganadores y
perdedores a los partidos posteriores dentro de datos/partidos_2026.json.

No edita mundial.ics directamente. El workflow lo regenera únicamente cuando
este script detecta cambios públicos en el calendario.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos" / "partidos_2026.json"
API_URL = "https://v3.football.api-sports.io/fixtures"
CDMX = ZoneInfo("America/Mexico_City")

# Solo se consulta durante la fase eliminatoria. Fuera de estas fechas no consume API.
INICIO_TORNEO = datetime(2026, 6, 28, tzinfo=CDMX).date()
FIN_TORNEO = datetime(2026, 7, 19, tzinfo=CDMX).date()

ESTADOS_FINALES = {"FT", "AET", "PEN", "AWD", "WO"}
BANDERA_INGLATERRA = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"

# API-Football devuelve nombres en inglés. Esta tabla impide que esos nombres lleguen
# al calendario público. Incluye variantes habituales del proveedor.
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
    "Colombia": ("Colombia", "🇨🇴"),
    "Ghana": ("Ghana", "🇬🇭"),
    "Australia": ("Australia", "🇦🇺"),
    "Egypt": ("Egipto", "🇪🇬"),
}

# Definición estable del cuadro. El primer valor es el resultado que viaja,
# seguido del partido destino y el lado donde debe colocarse.
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

CLAVES_DE_FASE: dict[str, tuple[str, ...]] = {
    "Dieciseisavos de final": ("round of 32",),
    "Octavos de final": ("round of 16",),
    "Cuartos de final": ("quarter-final", "quarterfinal"),
    "Semifinal": ("semi-final", "semifinal"),
    "Partido por el tercer lugar": ("3rd place", "third place"),
    "Final": ("final",),
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


def fecha_hora_cdmx(fixture: dict[str, Any]) -> tuple[str, str]:
    bruto = fixture.get("fixture", {})
    marca = bruto.get("timestamp")
    if isinstance(marca, (int, float)):
        fecha = datetime.fromtimestamp(marca, tz=CDMX)
    else:
        texto = str(bruto.get("date", ""))
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        fecha = datetime.fromisoformat(texto).astimezone(CDMX)
    return fecha.strftime("%Y-%m-%d"), fecha.strftime("%H:%M")


def fase_compatible(partido: dict[str, Any], fixture: dict[str, Any]) -> bool:
    ronda = str(fixture.get("league", {}).get("round", "")).casefold()
    fase = str(partido.get("fase", ""))
    claves = CLAVES_DE_FASE.get(fase, ())

    if fase == "Final":
        return ronda.strip() in {"final", "final - 1"}
    return any(clave in ronda for clave in claves)


def obtener_fixtures(clave: str) -> list[dict[str, Any]]:
    """Obtiene todos los partidos del Mundial; maneja paginación si el API la activa."""
    resultados: list[dict[str, Any]] = []
    pagina = 1

    while True:
        parametros = urlencode(
            {
                "league": "1",
                "season": "2026",
                "timezone": "America/Mexico_City",
                "page": pagina,
            }
        )
        peticion = Request(
            f"{API_URL}?{parametros}",
            headers={"x-apisports-key": clave},
        )

        try:
            with urlopen(peticion, timeout=30) as respuesta:
                contenido = json.loads(respuesta.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"API-Football respondió HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("No fue posible contactar API-Football.") from exc

        errores = contenido.get("errors")
        if errores:
            raise RuntimeError(f"API-Football devolvió un error: {errores}")

        respuesta_api = contenido.get("response")
        if not isinstance(respuesta_api, list):
            raise RuntimeError("La respuesta de API-Football no contiene una lista de partidos.")

        resultados.extend(respuesta_api)
        total = int(contenido.get("paging", {}).get("total", 1) or 1)
        if pagina >= total:
            break
        pagina += 1

    return resultados


def equipo_en_espanol(nombre_origen: Any) -> tuple[str, str]:
    nombre = str(nombre_origen or "").strip()
    if nombre not in INGLES_A_ESPANOL:
        raise ValueError(
            f"El proveedor devolvió un equipo no contemplado: {nombre!r}. "
            "No se escribirá ningún nombre en inglés en el calendario."
        )
    return INGLES_A_ESPANOL[nombre]


def cambiar(partido: dict[str, Any], campo: str, valor: Any, publico: bool = True) -> bool:
    if partido.get(campo) == valor:
        return False
    partido[campo] = valor
    if publico:
        partido["revision"] = int(partido.get("revision", 0)) + 1
    return True


def asignar_equipo(partido: dict[str, Any], lado: str, equipo: tuple[str, str]) -> bool:
    if lado not in {"local", "visitante"}:
        raise ValueError(f"Lado no válido: {lado}")
    nombre, bandera = equipo
    cambio = False
    cambio |= cambiar(partido, f"equipo_{lado}", nombre)
    cambio |= cambiar(partido, f"bandera_{lado}", bandera)
    return cambio


def localizar_partido(
    fixture: dict[str, Any],
    por_numero: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    fixture_id = fixture.get("fixture", {}).get("id")
    if fixture_id is not None:
        for partido in por_numero.values():
            if str(partido.get("api_fixture_id", "")) == str(fixture_id):
                return partido

    fecha, hora = fecha_hora_cdmx(fixture)
    candidatos = [
        partido
        for partido in por_numero.values()
        if partido.get("fecha") == fecha
        and partido.get("hora") == hora
        and fase_compatible(partido, fixture)
    ]

    if len(candidatos) == 1:
        return candidatos[0]
    return None


def resultado_final(fixture: dict[str, Any]) -> tuple[tuple[str, str], tuple[str, str]] | None:
    estado = str(fixture.get("fixture", {}).get("status", {}).get("short", "")).upper()
    if estado not in ESTADOS_FINALES:
        return None

    equipos = fixture.get("teams", {})
    local = equipos.get("home", {})
    visitante = equipos.get("away", {})

    if local.get("winner") is True:
        return equipo_en_espanol(local.get("name")), equipo_en_espanol(visitante.get("name"))
    if visitante.get("winner") is True:
        return equipo_en_espanol(visitante.get("name")), equipo_en_espanol(local.get("name"))
    return None


def sincronizar(datos: dict[str, Any], fixtures: list[dict[str, Any]]) -> tuple[bool, dict[str, int]]:
    partidos = datos.get("partidos", [])
    por_numero = {int(partido["numero"]): partido for partido in partidos}
    cambio_total = False
    resumen = {"asignados": 0, "finalizados": 0, "sin_asignar": 0}

    for fixture in fixtures:
        partido = localizar_partido(fixture, por_numero)
        if partido is None:
            continue

        resumen["asignados"] += 1
        bruto = fixture.get("fixture", {})
        fixture_id = bruto.get("id")
        if fixture_id is not None:
            cambio_total |= cambiar(partido, "api_fixture_id", int(fixture_id), publico=False)

        fecha, hora = fecha_hora_cdmx(fixture)
        cambio_total |= cambiar(partido, "fecha", fecha)
        cambio_total |= cambiar(partido, "hora", hora)

        equipos = fixture.get("teams", {})
        local = equipos.get("home", {})
        visitante = equipos.get("away", {})

        # Si el API ya conoce ambos participantes, actualiza nombre y bandera incluso
        # antes del silbatazo final. Esto llena automáticamente cada cruce siguiente.
        nombre_local = str(local.get("name") or "").strip()
        nombre_visitante = str(visitante.get("name") or "").strip()
        if nombre_local in INGLES_A_ESPANOL and nombre_visitante in INGLES_A_ESPANOL:
            cambio_total |= asignar_equipo(partido, "local", equipo_en_espanol(nombre_local))
            cambio_total |= asignar_equipo(partido, "visitante", equipo_en_espanol(nombre_visitante))
        elif nombre_local or nombre_visitante:
            # Antes de que se resuelva un cruce, algunos proveedores envían TBD.
            # Se conserva el texto español existente y no se publica ningún valor inglés.
            print(
                f"Partido {partido['numero']}: participantes aún no disponibles "
                f"en español ({nombre_local or '—'} vs {nombre_visitante or '—'})."
            )

        final = resultado_final(fixture)
        if final is None:
            continue

        resumen["finalizados"] += 1
        ganador, perdedor = final
        marcador = fixture.get("goals", {})
        datos_resultado = {
            "estado": "Finalizado",
            "marcador_local": marcador.get("home"),
            "marcador_visitante": marcador.get("away"),
            "ganador": ganador[0],
        }
        cambio_total |= cambiar(partido, "resultado", datos_resultado, publico=False)

        for tipo, destino_numero, lado in DESTINOS.get(int(partido["numero"]), []):
            destino = por_numero[destino_numero]
            equipo = ganador if tipo == "ganador" else perdedor
            cambio_total |= asignar_equipo(destino, lado, equipo)

    resumen["sin_asignar"] = len(fixtures) - resumen["asignados"]
    return cambio_total, resumen


def main() -> int:
    hoy = datetime.now(CDMX).date()
    if not (INICIO_TORNEO <= hoy <= FIN_TORNEO):
        print("Fuera de la fase eliminatoria: no se consulta API-Football.")
        return 0

    clave = os.environ.get("API_FOOTBALL_KEY", "").strip()
    if not clave:
        print("Falta el secreto API_FOOTBALL_KEY.", file=sys.stderr)
        return 2

    datos = cargar_datos()
    fixtures = obtener_fixtures(clave)
    cambio, resumen = sincronizar(datos, fixtures)

    if not cambio:
        print(
            "Sin cambios. "
            f"Partidos asignados: {resumen['asignados']}; "
            f"finalizados: {resumen['finalizados']}."
        )
        return 0

    datos["actualizado_en"] = ahora_utc()
    guardar_datos(datos)
    print(
        "Datos actualizados. "
        f"Partidos asignados: {resumen['asignados']}; "
        f"finalizados: {resumen['finalizados']}; "
        f"sin asignar: {resumen['sin_asignar']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
