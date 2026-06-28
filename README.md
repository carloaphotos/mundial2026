# Calendario Mundial 2026

El único archivo que se publica y se comparte es **`mundial.ics`**.  
No lo renombres ni lo muevas: mantener esa ruta es lo que conserva el mismo enlace de suscripción.

Este repositorio contiene los últimos 32 partidos: dieciseisavos, octavos, cuartos, semifinales, partido por el tercer lugar y final. Los horarios están convertidos a Ciudad de México.

## Estructura

```text
.
├── mundial.ics
├── generar_calendario.py
├── validar_calendario.py
├── datos/
│   └── partidos_2026.json
└── .github/
    └── workflows/
        └── validar.yml
```

- `mundial.ics`: el feed público que se suscribe en calendarios.
- `datos/partidos_2026.json`: fuente editable de los partidos.
- `generar_calendario.py`: crea el `.ics` sin editarlo manualmente.
- `validar_calendario.py`: revisa sintaxis, UTF-8, español, banderas, ubicación, notas y alarmas.
- `.github/workflows/validar.yml`: ejecuta la revisión automáticamente en cada actualización.

## Publicar en GitHub Pages

1. Crea un repositorio público, por ejemplo `calendario-mundial`.
2. Sube **todo** el contenido de esta carpeta a la raíz del repositorio.
3. En GitHub entra a **Settings → Pages**.
4. En **Build and deployment**, selecciona:
   - **Source:** Deploy from a branch
   - **Branch:** `main`
   - **Folder:** `/ (root)`
5. Guarda y espera a que GitHub publique el sitio.

El enlace de suscripción será:

```text
https://TU_USUARIO.github.io/calendario-mundial/mundial.ics
```

Si el repositorio se llama exactamente `TU_USUARIO.github.io`, el enlace será:

```text
https://TU_USUARIO.github.io/mundial.ics
```

## Suscribirse

- **iPhone / iPad:** Calendario → Calendarios → Agregar calendario → Agregar calendario de suscripción.
- **macOS:** Calendario → Archivo → Nueva suscripción de calendario.
- **Google Calendar (web):** Otros calendarios → + → Desde URL.
- **Outlook en la web:** Agregar calendario → Suscribirse desde la web.
- **Android:** Agrega la URL en Google Calendar web; después aparece en la app de Google Calendar.

Pega siempre la URL HTTPS de `mundial.ics`. No descargues ni importes el archivo si quieres recibir cambios futuros.

## Actualizar resultados o cruces

1. Abre `datos/partidos_2026.json`.
2. Sustituye los equipos provisionales por los equipos reales, junto con sus banderas.
3. Si cambia horario, sede, ciudad, fase o partido siguiente, modifica ese registro.
4. Aumenta `revision` en el partido que cambiaste.
5. En Terminal, dentro de la carpeta del repositorio, ejecuta:

```bash
python3 generar_calendario.py --actualizar-marca
python3 validar_calendario.py
```

6. Revisa el cambio y publícalo:

```bash
git status
git add mundial.ics datos/partidos_2026.json
git commit -m "Actualiza cruces del Mundial"
git push
```

GitHub Pages conservará la misma URL. Las personas suscritas recibirán la versión nueva cuando su aplicación vuelva a consultar el feed.

## Reglas importantes

- Conserva siempre el nombre **`mundial.ics`**.
- No crees `mundial_v2.ics`, `mundial_espanol.ics` ni copias paralelas.
- No cambies los `UID` generados: así las apps reconocen que un evento existente fue actualizado.
- Usa siempre nombres en español: `Sudáfrica`, `Países Bajos`, `Costa de Marfil`, `Estados Unidos`, `Bosnia y Herzegovina`, `RD Congo`, etc.
- El archivo usa `TZID=America/Mexico_City`, una definición VTIMEZONE y alarmas 30 minutos antes.
- El texto `\n` dentro de la fuente `.ics` es el escape oficial RFC 5545 para saltos de línea. En iPhone, Mac, Google Calendar y Outlook se verá como líneas separadas, no como los caracteres `\n`.

## Actualizaciones automáticas

Una suscripción conserva la URL y consulta el archivo de nuevo de forma automática. Apple Calendar permite ajustar la actualización automática de calendarios suscritos; Outlook también actualiza suscripciones en segundo plano. Google Calendar controla su propia frecuencia de consulta y puede tardar varias horas; ningún archivo `.ics` puede obligarlo a actualizar de inmediato.

El archivo incluye `REFRESH-INTERVAL` y `X-PUBLISHED-TTL` como sugerencia no invasiva para clientes que los respeten.

## Reutilizar la estructura en 2030, Eurocopa o Copa América

Duplica el archivo de datos, cambia competición, partidos, zona horaria y sedes, y conserva el generador y validador. Para otro torneo, publica su propio `*.ics` con un nombre estable desde el primer día.
