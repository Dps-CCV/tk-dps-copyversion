"""
Worker thread: porta la lógica de copia de ambos scripts Celery
(modo estándar y modo 22Dogs) sin dependencias de Celery ni webapp.

Emite señales Qt para actualizar la UI de progreso.
"""

import io
import os
import pprint
import subprocess
import sys
from datetime import date, datetime
from io import BytesIO

import urllib.request
import xlsxwriter
from PIL import Image

from sgtk.platform.qt import QtCore


class CopyWorker(QtCore.QThread):
    """
    Ejecuta la copia en background y emite señales de progreso.

    Señales:
        progress(current, total, description)  — actualiza la barra
        log_line(str)                          — línea de texto para el log
        finished(bool, str)                    — éxito/error + mensaje final
    """

    progress = QtCore.Signal(int, int, str)
    log_line = QtCore.Signal(str)
    finished = QtCore.Signal(bool, str)

    def __init__(
        self,
        sg,
        project,
        version_ids,
        title,
        description,
        method,
        include_dailies,
        mode_22dogs,
        logo_path="",
        parent=None,
    ):
        super(CopyWorker, self).__init__(parent)
        self._sg = sg
        self._project = project          # dict {'type': 'Project', 'id': ..., 'name': ...}
        self._version_ids = version_ids  # list[int]
        self._title = title
        self._description = description
        self._method = method
        self._include_dailies = include_dailies
        self._mode_22dogs = mode_22dogs
        self._logo_path = logo_path
        self._abort = False

    def abort(self):
        self._abort = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, current, total, desc):
        self.progress.emit(current, total, desc)
        self.log_line.emit(desc)

    def _log(self, msg):
        self.log_line.emit(str(msg))

    def _get_drive_letter(self, server_field):
        """Devuelve la letra de unidad mapeada según el servidor del proyecto."""
        if server_field and "MAGMA3" in server_field.upper():
            return "W:\\"
        return "P:\\"

    def _run_robocopy(self, src, dst, extra_args="", file_filter=""):
        """
        Lanza robocopy y emite cada línea de salida como log_line.
        Devuelve el return code.
        """
        if file_filter:
            cmd = f'robocopy "{src}" "{dst}" "{file_filter}" /MT:12 /J'
        else:
            cmd = f'robocopy "{src}" "{dst}" {extra_args} /MT:12 /J'

        self._log(f"  $ {cmd}")
        with subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self._log(line)
            return proc.wait()

    # ------------------------------------------------------------------
    # Excel helpers
    # ------------------------------------------------------------------

    def _build_workbook(self, path):
        """Crea el workbook con todos los formatos reutilizados."""
        wb = xlsxwriter.Workbook(path)
        ws = wb.add_worksheet(os.path.basename(path))

        def fmt(**kw):
            f = wb.add_format()
            for k, v in kw.items():
                getattr(f, f"set_{k}")(v)
            return f

        title_fmt = wb.add_format()
        title_fmt.set_align("center")
        title_fmt.set_align("bottom")
        title_fmt.set_font_name("Helvetica")
        title_fmt.set_bold()
        title_fmt.set_font_size(10)
        title_fmt.set_bg_color("#8EA9DB")
        title_fmt.set_text_wrap()
        title_fmt.set_border(1)
        title_fmt.set_border_color("black")
        title_fmt.set_top(5)
        title_fmt.set_top_color("black")
        title_fmt.set_bottom(5)
        title_fmt.set_bottom_color("black")

        cell_fmt = wb.add_format()
        cell_fmt.set_align("left")
        cell_fmt.set_align("bottom")
        cell_fmt.set_font_name("Helvetica")
        cell_fmt.set_font_size(10)
        cell_fmt.set_text_wrap()
        cell_fmt.set_border(1)
        cell_fmt.set_border_color("black")

        cutout_fmt = wb.add_format()
        cutout_fmt.set_num_format("0.00")
        cutout_fmt.set_align("right")
        cutout_fmt.set_align("bottom")
        cutout_fmt.set_font_name("Helvetica")
        cutout_fmt.set_font_size(10)
        cutout_fmt.set_text_wrap()
        cutout_fmt.set_border(1)
        cutout_fmt.set_border_color("black")
        cutout_fmt.set_right(2)
        cutout_fmt.set_right_color("black")

        number_fmt = wb.add_format()
        number_fmt.set_num_format("0.00")
        number_fmt.set_align("right")
        number_fmt.set_align("bottom")
        number_fmt.set_font_name("Helvetica")
        number_fmt.set_font_size(10)
        number_fmt.set_text_wrap()
        number_fmt.set_border(1)
        number_fmt.set_border_color("black")

        marco_fmt = wb.add_format()
        marco_fmt.set_border(2)
        marco_fmt.set_border_color("white")
        for side in ("bottom", "top", "right", "left"):
            getattr(marco_fmt, f"set_{side}")(1)
            getattr(marco_fmt, f"set_{side}_color")("white")

        return wb, ws, title_fmt, cell_fmt, cutout_fmt, number_fmt, marco_fmt

    def _write_sheet_header(self, ws, wb, title_fmt, marco_fmt):
        cols = [
            "Version", "Thumbnail", "Shot_code",
            "VFX", "Notes", "Duration", "Cut_In", "Cut_Out",
        ]
        for i, col in enumerate(cols):
            ws.write(7, i, col, title_fmt)
            ws.set_column(i, i, len(col) + 20)

        ws.set_column(0, 0, 8.5)
        ws.set_column(1, 1, 35)
        ws.set_column(4, 4, 40)  # Notes más ancha

        if self._logo_path and os.path.exists(self._logo_path):
            ws.insert_image("A1", self._logo_path, {"x_scale": 1, "y_scale": 1})

        return cols

    def _write_shot_row(self, ws, idx, shot_data, version_name,
                        cell_fmt, cutout_fmt, number_fmt,
                        version_description="", cell_height=140):
        """Escribe una fila completa de shot en la hoja Excel."""
        cell_width = 35
        ws.write(idx + 8, 0, version_name, cell_fmt)
        ws.set_column(0, 0, len(version_name) + 20)

        # Notes — description de la versión (no del shot)
        ws.write(idx + 8, 4, version_description or "", cell_fmt)

        for cell in shot_data:
            if cell in ("id", "type"):
                continue

            if cell == "image":
                ws.set_row(idx + 8, cell_height)
                ws.write(idx + 8, 1, "", cell_fmt)
                url = str(shot_data[cell])
                if url != "None":
                    try:
                        name_short = url.rsplit("/", 1)[1]
                        if "?" in name_short:
                            name_short = name_short[: name_short.find("?")]
                        with urllib.request.urlopen(url, timeout=15) as _resp:
                            image_data = BytesIO(_resp.read())
                        im = Image.open(image_data)
                        im.thumbnail((500, 500), Image.LANCZOS)
                        pic_w, pic_h = im.size
                        im_bytes = io.BytesIO()
                        im.save(im_bytes, format="PNG")

                        x_scale_ver = ws._size_col(1) / pic_w
                        cell_y_scale = (pic_h * x_scale_ver) * (
                            cell_height / ws._size_row(idx + 8)
                        )
                        x_scale = (ws._size_col(1) - ws._size_col(1) / 20) / pic_w
                        pix_ratio_w = ws._size_col(1) / cell_width

                        ws.insert_image(
                            idx + 8, 1, name_short,
                            {
                                "image_data": im_bytes,
                                "x_scale": x_scale,
                                "y_scale": x_scale,
                                "x_offset": int((cell_width / 20) * pix_ratio_w),
                                "y_offset": int(cell_y_scale / 20),
                                "object_position": 2,
                            },
                        )
                        ws.set_row(idx + 8, cell_y_scale)
                    except Exception as e:
                        self._log(f"  [WARN] No se pudo insertar thumbnail: {e}")
            else:
                if isinstance(shot_data[cell], dict):
                    element = shot_data[cell].get("name", "")
                else:
                    element = "" if str(shot_data[cell]) == "None" else str(shot_data[cell])

                col_map = {
                    "code": (2, cell_fmt),
                    "sg_efecto_a_hacer": (3, cell_fmt),
                    # columna 4 = Notes, escrita arriba desde version_description
                    "sg_cut_duration": (5, number_fmt),
                    "sg_cut_in": (6, number_fmt),
                    "sg_cut_out": (7, cutout_fmt),
                }
                if cell in col_map:
                    col_idx, fmt = col_map[cell]
                    val = int(element) if cell in ("sg_cut_duration", "sg_cut_in", "sg_cut_out") and element else element
                    ws.write(idx + 8, col_idx, val, fmt)
                    ws.set_column(col_idx, col_idx, len(str(element)) + 20)

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self):
        try:
            if self._mode_22dogs:
                self._run_22dogs()
            else:
                self._run_standard()
        except Exception as e:
            import traceback
            self.finished.emit(False, f"Error: {e}\n{traceback.format_exc()}")

    # ------------------------------------------------------------------
    # Modo estándar
    # ------------------------------------------------------------------

    def _run_standard(self):
        sg = self._sg
        project_id = self._project["id"]
        version_ids = self._version_ids
        date_number = date.today().strftime("%Y%m%d")

        self._log(f"[{datetime.now()}] Iniciando modo estándar")

        # Datos del proyecto
        proj = sg.find_one(
            "Project",
            [["id", "is", project_id]],
            ["sg_cliente", "sg_dps_server", "name"],
        )
        drive = self._get_drive_letter(proj.get("sg_dps_server", ""))
        project_name = proj["name"]
        envios_root = os.path.normpath(os.path.join(drive, project_name, "ENVIOS"))
        self._log(f"Envíos root: {envios_root}")

        # Deliveries existentes (para número correlativo)
        deliveries = sg.find("Delivery", [["project.Project.id", "is", project_id]])

        # Published files
        filters = [
            ["version.Version.id", "in", version_ids],
            ["project", "is", {"type": "Project", "id": project_id}],
            ["code", "contains", ".%04d."],
        ]
        fields = [
            "path", "entity", "version", "project",
            "project.Project.name", "project.Project.sg_dps_server",
            "version.Version.sg_path_to_movie",
            "version.Version.description",
        ]
        path_dict = sg.find("PublishedFile", filters, fields)
        total = len(path_dict)
        versions_created = []

        # Excel
        report_name = (
            f"report_{date_number}_{str(len(deliveries) + 1).zfill(5)}.xlsx"
        )
        report_path = os.path.normpath(os.path.join(envios_root, report_name))
        wb, ws, title_fmt, cell_fmt, cutout_fmt, number_fmt, marco_fmt = (
            self._build_workbook(report_path)
        )
        self._write_sheet_header(ws, wb, title_fmt, marco_fmt)

        for idx, pub in enumerate(path_dict):
            if self._abort:
                wb.close()
                self.finished.emit(False, "Cancelado por el usuario.")
                return

            # Ruta de render
            path_info = pub["path"]
            if path_info["link_type"] == "local":
                render_file = os.path.normpath(path_info["local_path"])
            else:
                render_file = os.path.normpath(
                    path_info["url"].replace("file:///", "")
                )

            versions_created.append(pub["version"])
            render_str = pub["version"]["name"].replace(".%04d", "")
            shot_folder = render_str.upper().replace(" ", "_")

            envios_folder = os.path.normpath(
                os.path.join(envios_root, date_number, shot_folder)
            )
            envios_dailies = os.path.normpath(
                os.path.join(envios_root, date_number, "DAILIES")
            )
            render_folder = os.path.normpath(os.path.dirname(render_file))

            os.makedirs(envios_folder, exist_ok=True)

            self._emit(idx + 1, total, f"Copiando: {shot_folder}")
            self._run_robocopy(render_folder, envios_folder, extra_args="/E")

            # Dailies
            if self._include_dailies:
                mov_path = pub.get("version.Version.sg_path_to_movie")
                if mov_path:
                    try:
                        dailies_src = os.path.normpath(os.path.dirname(mov_path))
                        dailies_file = os.path.basename(mov_path)
                        os.makedirs(envios_dailies, exist_ok=True)
                        self._emit(idx + 1, total, f"Copiando dailies: {dailies_file}")
                        self._run_robocopy(dailies_src, envios_dailies, file_filter=dailies_file)
                    except Exception as e:
                        self._log(f"  [WARN] Dailies: {e}")

            # Shot data para Excel
            shot_data = sg.find_one(
                "Shot",
                [["id", "is", pub["entity"]["id"]]],
                ["code", "image", "sg_efecto_a_hacer", "description",
                 "sg_cut_duration", "sg_cut_in", "sg_cut_out"],
            )
            ver_desc = pub.get("version.Version.description") or ""
            self._write_shot_row(
                ws, idx, shot_data, pub["version"]["name"],
                cell_fmt, cutout_fmt, number_fmt,
                version_description=ver_desc,
            )

        self._finalize(
            sg, proj, envios_root, wb, ws, marco_fmt,
            report_name, report_path, deliveries,
            versions_created, version_ids, drive,
        )

    # ------------------------------------------------------------------
    # Modo 22Dogs
    # ------------------------------------------------------------------

    def _run_22dogs(self):
        sg = self._sg
        project_id = self._project["id"]
        version_ids = self._version_ids
        date_number = date.today().strftime("%Y%m%d")

        self._log(f"[{datetime.now()}] Iniciando modo 22Dogs")

        proj = sg.find_one(
            "Project",
            [["id", "is", project_id]],
            ["sg_cliente", "sg_dps_server", "name"],
        )
        drive = self._get_drive_letter(proj.get("sg_dps_server", ""))
        project_name = proj["name"]
        envios_root = os.path.normpath(os.path.join(drive, project_name, "ENVIOS"))
        self._log(f"Envíos root: {envios_root}")

        deliveries = sg.find("Delivery", [["project.Project.id", "is", project_id]])

        filters = [
            ["version.Version.id", "in", version_ids],
            ["project", "is", {"type": "Project", "id": project_id}],
            ["code", "contains", ".%04d."],
        ]
        fields = [
            "path", "entity", "version", "project",
            "project.Project.name", "project.Project.sg_dps_server",
            "version.Version.sg_path_to_movie",
            "version.Version.description",
        ]
        path_dict = sg.find("PublishedFile", filters, fields)
        total = len(path_dict)
        versions_created = []

        report_name = (
            f"report_{date_number}_{str(len(deliveries) + 1).zfill(5)}.xlsx"
        )
        report_path = os.path.normpath(os.path.join(envios_root, report_name))
        wb, ws, title_fmt, cell_fmt, cutout_fmt, number_fmt, marco_fmt = (
            self._build_workbook(report_path)
        )
        self._write_sheet_header(ws, wb, title_fmt, marco_fmt)

        for idx, pub in enumerate(path_dict):
            if self._abort:
                wb.close()
                self.finished.emit(False, "Cancelado por el usuario.")
                return

            path_info = pub["path"]
            if path_info["link_type"] == "local":
                render_file = os.path.normpath(path_info["local_path"])
            else:
                render_file = os.path.normpath(
                    path_info["url"].replace("file:///", "")
                )

            versions_created.append(pub["version"])
            render_str = pub["version"]["name"].replace(".%04d", "")
            render_str_upper = render_str.upper()

            # 22Dogs: shotFolder en lower, con subcarpetas Comp/exr y Comp/mov
            shot_folder = (
                render_str_upper.replace(" ", "_").lower().replace("dmr", "DMR")
            )

            envios_folder = os.path.normpath(
                os.path.join(envios_root, date_number, "Comp", shot_folder, "exr")
            )
            envios_dailies = os.path.normpath(
                os.path.join(envios_root, date_number, "Comp", shot_folder, "mov")
            )
            render_folder = os.path.normpath(os.path.dirname(render_file))

            os.makedirs(envios_folder, exist_ok=True)

            self._emit(idx + 1, total, f"Copiando [22Dogs]: {shot_folder}")
            self._run_robocopy(render_folder, envios_folder, extra_args="/E")

            # Renombrar Comp → comp en los archivos copiados
            for f in os.listdir(envios_folder):
                old = os.path.join(envios_folder, f)
                new = os.path.join(envios_folder, f.replace("Comp", "comp"))
                if old != new:
                    os.rename(old, new)

            # Dailies 22Dogs
            if self._include_dailies:
                mov_path = pub.get("version.Version.sg_path_to_movie")
                if mov_path:
                    try:
                        dailies_src = os.path.normpath(os.path.dirname(mov_path))
                        dailies_file = os.path.basename(mov_path).replace("Comp", "comp")
                        os.makedirs(envios_dailies, exist_ok=True)
                        self._emit(idx + 1, total, f"Copiando dailies [22Dogs]: {dailies_file}")
                        self._run_robocopy(dailies_src, envios_dailies, file_filter=dailies_file)
                    except Exception as e:
                        self._log(f"  [WARN] Dailies 22Dogs: {e}")

            shot_data = sg.find_one(
                "Shot",
                [["id", "is", pub["entity"]["id"]]],
                ["code", "image", "sg_efecto_a_hacer", "description",
                 "sg_cut_duration", "sg_cut_in", "sg_cut_out"],
            )
            ver_desc = pub.get("version.Version.description") or ""
            self._write_shot_row(
                ws, idx, shot_data, pub["version"]["name"],
                cell_fmt, cutout_fmt, number_fmt,
                version_description=ver_desc,
            )

        # ---- Generar CSV de submission ----
        self._write_22dogs_csv(envios_root, date_number, path_dict)

        self._finalize(
            sg, proj, envios_root, wb, ws, marco_fmt,
            report_name, report_path, deliveries,
            versions_created, version_ids, drive,
        )

    # ------------------------------------------------------------------
    # CSV de submission para 22Dogs
    # ------------------------------------------------------------------

    def _write_22dogs_csv(self, envios_root, date_number, path_dict):
        """
        Genera DMR5_Submission_CV_YYYYMMDD.csv en la carpeta de ENVIOS.
        Columnas: name, status, note
        """
        import csv
        import re
        csv_name = f"DMR5_Submission_CV_{date_number}.csv"
        csv_path = os.path.normpath(os.path.join(envios_root, csv_name))
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "status", "note"])
                for pub in path_dict:
                    version_name = pub["version"]["name"].replace(".%04d", "")
                    # Sustituir _comp_ o _Comp_ (cualquier capitalización)
                    csv_name_val = re.sub(r"_[Cc]omp_", "_compositing_", version_name)
                    description = pub.get("version.Version.description") or ""
                    writer.writerow([csv_name_val, "Published", description])
            self._log(f"CSV generado: {csv_path}")
        except Exception as e:
            self._log(f"[WARN] No se pudo generar el CSV: {e}")

    # ------------------------------------------------------------------
    # Finalización común: cierre Excel, Delivery, update versions
    # ------------------------------------------------------------------

    def _finalize(
        self, sg, proj, envios_root, wb, ws, marco_fmt,
        report_name, report_path, deliveries,
        versions_created, version_ids, drive,
    ):
        self._emit(len(version_ids), len(version_ids),
                   "Copia completada. Actualizando FPT…")

        # Marco blanco encima del logo
        for i in range(7):
            for a in range(12):
                ws.write(i, a, "", marco_fmt)
        wb.close()

        # Adjuntar reporte a FPT
        # La ruta del attach usa la letra de unidad mapeada
        attach_path = report_path
        data_attach = {
            "this_file": {
                "link_type": "local",
                "local_path": attach_path,
            }
        }
        attach = [sg.create("Attachment", data_attach)]

        # Crear Delivery
        delivery_data = {
            "delivery_number": str(len(deliveries) + 1).zfill(5),
            "title": self._title,
            "description": self._description,
            "sg_delivery_method": self._method,
            "sg_due_date": datetime.now(),
            "project": proj,
            "version_sg_deliveries_versions": versions_created,
            "attachments": attach,
        }
        recipient = proj.get("sg_cliente")
        if recipient:
            delivery_data["addressings_to"] = [recipient]
        sg.create("Delivery", delivery_data)
        self._log("Delivery creado en FPT.")

        # Actualizar versiones → Delivered
        deliver_date = date.today().strftime("%Y-%m-%d")
        batch = [
            {
                "request_type": "update",
                "entity_type": "Version",
                "entity_id": int(vid),
                "data": {
                    "sg_to_deliver___delivered": "Delivered",
                    "sg_delivered_date": str(deliver_date),
                },
            }
            for vid in version_ids
        ]
        sg.batch(batch)
        self._log("Versiones actualizadas en FPT.")

        # Log en disco
        log_file = os.path.join(envios_root, "Envioslog.txt").replace("\\", "/")
        try:
            with open(log_file, "a") as fh:
                fh.write(
                    f"\n[{datetime.now()}] Delivery {delivery_data['delivery_number']}"
                    f" — {self._title}\n"
                )
        except Exception as e:
            self._log(f"[WARN] No se pudo escribir log: {e}")

        self.finished.emit(True, "¡Proceso completado con éxito!")