# Guía de integración — tk-dps-copyversion
## Efectoscopio Pipeline

---

## 1. Estructura del repositorio

Crea un repo Git separado para la app (recomendado):

```
tk-dps-copyversion/
├── app.py                  ← entry point de la app
├── info.yml                ← manifiesto (nombre, versión, configuración)
├── INTEGRACION.md          ← esta guía
└── python/
    ├── __init__.py
    ├── dialog.py           ← UI principal (tabs, filtros, tabla de versiones)
    └── worker.py           ← lógica de copia + Excel + FPT (sin Celery)
```

Sube el repo a GitHub (ej: `Dps-CCV/tk-dps-copyversion`) y crea un tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## 2. Registrar la app en tu pipeline config

### 2a. Declarar la localización en `app_locations.yml`

En `DPS_SHOTGRID_CONFIG/config/env/includes/app_locations.yml`, añade:

```yaml
apps.tk-dps-copyversion.location:
  type: git
  path: https://github.com/Dps-CCV/tk-dps-copyversion.git
  version: v1.0.0
```

Si prefieres tenerla como carpeta local durante desarrollo (sin push cada vez):

```yaml
apps.tk-dps-copyversion.location:
  type: dev
  path: C:/sgtk/dev/tk-dps-copyversion
```

### 2b. Añadir la app al entorno `tk-shotgun`

Abre el fichero de entorno donde configures `tk-shotgun`
(normalmente `config/env/shotgun_globals.yml` o similar) y añade la app:

```yaml
engines:
  tk-shotgun:
    apps:

      # ... tus apps existentes ...

      tk-dps-copyversion:
        location: "@apps.tk-dps-copyversion.location"
        logo_path: "P:/PIPELINE/recursos/Efectoscopio_Logotipo_FondoAmarilloLogoNegro_750.png"

    location:
      type: app_store
      name: tk-shotgun
      version: v0.9.4   # la que uses actualmente
```

> **Nota sobre `logo_path`:** usa la ruta con la unidad mapeada del PC del usuario
> (P: o W: según servidor). Si está vacía, el workbook se genera sin logo.

### 2c. Reload del entorno (desarrollo)

En ShotGrid Desktop, con el proyecto activo:

```
Admin → Advanced → Reload Engines and Apps
```

O desde una shell con sgtk bootstrap:

```python
import sgtk
tk = sgtk.sgtk_from_path("C:/ruta/al/proyecto")
tk.reload_templates()
```

---

## 3. Dependencias Python

La app usa las siguientes librerías que **no** vienen con sgtk por defecto.
Instálalas en el Python que usa ShotGrid Desktop / tk-shotgun:

```bash
pip install xlsxwriter pillow requests
```

En el Python embebido de ShotGrid Desktop (normalmente en
`C:/Program Files/Autodesk/ShotGrid Desktop/Python/python.exe`):

```bash
"C:/Program Files/Autodesk/ShotGrid Desktop/Python/python.exe" -m pip install xlsxwriter pillow requests
```

`shotgun_api3` ya está disponible en el entorno de toolkit.

---

## 4. Cómo aparece la app para el usuario

Una vez integrada:

1. El usuario abre **ShotGrid Desktop**
2. Selecciona el proyecto
3. En el panel de aplicaciones aparece **"Copy Version to Envíos"**
4. Al hacer clic se abre el diálogo con tres pestañas:

   **① Versiones** — Tabla de versiones del proyecto con:
   - Filtro por Playlist
   - Filtro por estado de entrega (Pendiente / Delivered)
   - Búsqueda libre por nombre de versión o shot
   - Thumbnails en línea
   - Selección múltiple

   **② Parámetros de entrega** — Formulario con:
   - Título y descripción del envío
   - Método de entrega (FTP, HDD, Link…)
   - Checkbox "Incluir dailies"
   - Checkbox "Modo 22Dogs" (estructura Comp/shot/exr + Comp/shot/mov)

   **③ Progreso** — Log en tiempo real + barra de progreso

---

## 5. Diferencias entre modo Estándar y modo 22Dogs

| | Estándar | 22Dogs |
|---|---|---|
| Carpeta de renders | `ENVIOS/YYYYMMDD/SHOT_FOLDER/` | `ENVIOS/YYYYMMDD/Comp/shot_folder/exr/` |
| Carpeta de dailies | `ENVIOS/YYYYMMDD/DAILIES/` | `ENVIOS/YYYYMMDD/Comp/shot_folder/mov/` |
| Case del nombre | MAYÚSCULAS | minúsculas (con `dmr` → `DMR`) |
| Rename Comp→comp | No | Sí, en archivos copiados |
| Dailies | Opcional (checkbox) | Opcional (checkbox) |

---

## 6. Distribuir por branches

Si tienes branches `master` y `22dogs` en tu pipeline config,
puedes apuntar cada branch a una versión distinta de la app:

```yaml
# En el branch 22dogs de DPS_SHOTGRID_CONFIG
apps.tk-dps-copyversion.location:
  type: git
  path: https://github.com/Dps-CCV/tk-dps-copyversion.git
  version: v1.1.0-22dogs

# En master
apps.tk-dps-copyversion.location:
  type: git
  path: https://github.com/Dps-CCV/tk-dps-copyversion.git
  version: v1.0.0
```

Aunque con el checkbox en la propia UI no necesitas branches distintos
para este caso.

---

## 7. Añadir la app a Nuke/Maya (opcional)

Si quieres que también esté disponible desde el menú de Nuke o Maya,
añádela en los entornos correspondientes:

```yaml
# config/env/asset_step.yml  (o shot_step.yml)
engines:
  tk-nuke:
    apps:
      tk-dps-copyversion:
        location: "@apps.tk-dps-copyversion.location"
        logo_path: ""
```

El registro en el menú de Nuke/Maya se hace automáticamente a través del
`engine.register_command()` en `app.py`.

---

## 8. Troubleshooting frecuente

**La app no aparece en ShotGrid Desktop**
→ Comprueba que el entorno `tk-shotgun` está activo para el proyecto.
→ Revisa el log de sgtk: `%APPDATA%/Shotgun/Logs/tk-shotgun.log`

**Error `No module named 'xlsxwriter'`**
→ La dependencia no está instalada en el Python de ShotGrid Desktop.
→ Ver paso 3 de esta guía.

**`sg_to_deliver___delivered` no existe**
→ El nombre del campo puede variar según tu schema.
→ Cámbialo en `worker.py` (línea del batch de actualización) y en
  `dialog.py` (filtro de status en `_apply_filters`).

**Las thumbnails no cargan**
→ Comprueba conectividad desde el PC a los CDN de ShotGrid.
→ El error se captura silenciosamente; el resto del proceso continúa.

**`Image.ANTIALIAS` deprecation warning (Pillow ≥ 10)**
→ Ya corregido en `worker.py` usando `Image.LANCZOS`.

---

## 9. Actualizar la app

1. Haz los cambios en el código
2. Crea un nuevo tag: `git tag v1.0.1 && git push origin v1.0.1`
3. Actualiza `app_locations.yml` con el nuevo tag
4. Haz "Reload Engines and Apps" en ShotGrid Desktop

No es necesario tocar ningún PC de usuario — sgtk descarga la nueva
versión automáticamente desde Git la próxima vez que se cargue el entorno.
