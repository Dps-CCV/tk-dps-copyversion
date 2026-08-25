"""
DPS Copy Version to Envíos — Toolkit App
Efectoscopio Pipeline
"""

import os
import sys
import sgtk
from sgtk.platform import Application


class DPSCopyVersionApp(Application):

    def init_app(self):
        self.engine.register_command(
            "Copy Version to Envios",
            self.show_dialog,
            {
                "short_name": "efectoscopio_copy_version",
                "description": "Copia renders seleccionados al directorio de envios y actualiza FPT.",
            },
        )

    def show_dialog(self):
        # Inyectar vendor/ y python/ en sys.path manualmente,
        # sin depender del mecanismo import_module de sgtk.
        app_root   = os.path.dirname(os.path.abspath(__file__))
        python_dir = os.path.join(app_root, "python")
        vendor_dir = os.path.join(app_root, "vendor")

        # Pillow: elegir carpeta según versión de Python en uso
        py_tag     = "cp%d%d" % (sys.version_info.major, sys.version_info.minor)
        pillow_dir = os.path.join(vendor_dir, "pillow_%s" % py_tag)
        if not os.path.isdir(pillow_dir):
            import glob
            candidates = sorted(glob.glob(os.path.join(vendor_dir, "pillow_cp*")))
            pillow_dir = candidates[-1] if candidates else None

        for path in [python_dir, vendor_dir, pillow_dir]:
            if path and path not in sys.path:
                sys.path.insert(0, path)

        # Import directo — ya está en sys.path
        import dialog as dialog_module

        self._dialog = self.engine.show_dialog(
            "EFECTOSCOPIOSSSSSS — Copy Version to Envios",
            self,
            dialog_module.AppDialog,
            self,
        )

    def destroy_app(self):
        self.log_debug("Destroying tk-dps-copyversion app")