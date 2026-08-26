"""
AppDialog — Ventana principal de Copy Version to Envios.
Efectoscopio Pipeline

Pestañas:
  1. Versiones  — tabla con filtros de campo, vista de playlist/thumbnail
  2. Entrega    — título, descripción, método, modo 22Dogs, dailies
  3. Progreso   — log en tiempo real + barra de progreso
"""

import os
import sgtk
from sgtk.platform.qt import QtCore, QtGui

from worker import CopyWorker


# ---------------------------------------------------------------------------
# Mapa de sedes → nombre de fichero de logo
# La clave es el valor del campo sg_sede_new.code en FPT
# ---------------------------------------------------------------------------
SEDE_LOGO_MAP = {
    "Madrid":   "logo_madrid.png",
    "Canarias": "logo_canarias.png",
    "Navarra":  "logo_navarra.png",
}


def resolve_logo(project_id, sg, app=None):
    """
    Devuelve la ruta absoluta al logo correcto según la sede del proyecto.

    Orden de resolución:
      1. resources/logo_<sede>.png  — si el proyecto tiene sede y existe el fichero
      2. resources/logo.png         — fallback genérico dentro del repo
      3. app.get_setting("logo_path") — fallback al yml de configuración
      4. ""                         — sin logo
    """
    resources_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "resources"
    )

    # Intentar obtener la sede del proyecto
    sede_logo = None
    try:
        proj = sg.find_one(
            "Project",
            [["id", "is", project_id]],
            ["sg_sede_new"],
        )
        sede = (proj or {}).get("sg_sede_new") or {}
        sede_code = sede.get("name") or sede.get("code") or ""
        filename = SEDE_LOGO_MAP.get(sede_code)
        if filename:
            candidate = os.path.join(resources_dir, filename)
            if os.path.exists(candidate):
                sede_logo = candidate
    except Exception:
        pass

    if sede_logo:
        return sede_logo

    # Fallback genérico en resources/
    generic = os.path.join(resources_dir, "logo.png")
    if os.path.exists(generic):
        return generic

    # Fallback al yml
    if app:
        return app.get_setting("logo_path", "")

    return ""


# ---------------------------------------------------------------------------
# Colores corporativos Efectoscopio
# ---------------------------------------------------------------------------
DARK_BG    = "#1A1A1A"
PANEL_BG   = "#242424"
ACCENT     = "#E8C840"   # amarillo logo
ACCENT2    = "#3A3A3A"
TEXT_MAIN  = "#F0F0F0"
TEXT_DIM   = "#888888"
SUCCESS    = "#5DBD73"
ERROR      = "#D95B5B"
BORDER     = "#3C3C3C"

STYLE = f"""
QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_MAIN};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 11px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {PANEL_BG};
}}

QTabBar::tab {{
    background: {DARK_BG};
    color: {TEXT_DIM};
    padding: 8px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    min-width: 100px;
}}

QTabBar::tab:selected {{
    background: {PANEL_BG};
    color: {ACCENT};
    border-top: 2px solid {ACCENT};
}}

QTabBar::tab:hover {{
    color: {TEXT_MAIN};
}}

QTableWidget {{
    background-color: {PANEL_BG};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    alternate-background-color: #2C2C2C;
    selection-background-color: #3D3519;
    selection-color: {ACCENT};
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

QHeaderView::section {{
    background-color: {ACCENT2};
    color: {TEXT_DIM};
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {BORDER};
    font-weight: bold;
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.5px;
}}

QLineEdit, QComboBox, QTextEdit, QSpinBox {{
    background-color: {ACCENT2};
    color: {TEXT_MAIN};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 5px 8px;
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {TEXT_DIM};
    margin-right: 6px;
}}

QPushButton {{
    background-color: {ACCENT2};
    color: {TEXT_MAIN};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 7px 18px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #484848;
    border-color: {TEXT_DIM};
}}

QPushButton#btn_run {{
    background-color: #E85C20;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 13px;
    padding: 9px 28px;
    border: none;
    border-radius: 4px;
    letter-spacing: 0.5px;
}}

QPushButton#btn_run:hover {{
    background-color: #FF6A2A;
}}

QPushButton#btn_run:disabled {{
    background-color: #5A3020;
    color: #8A6050;
}}

QPushButton#btn_cancel {{
    background-color: transparent;
    color: {ERROR};
    border: 1px solid {ERROR};
}}

QPushButton#btn_cancel:hover {{
    background-color: #3D1515;
}}

QProgressBar {{
    background-color: {ACCENT2};
    border: 1px solid {BORDER};
    border-radius: 3px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 2px;
}}

QCheckBox {{
    color: {TEXT_MAIN};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    background-color: {ACCENT2};
    border: 1px solid {BORDER};
    border-radius: 2px;
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QLabel#label_section {{
    color: {TEXT_DIM};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-top: 8px;
}}

QTextEdit#log_view {{
    background-color: #0F0F0F;
    color: #A8C890;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 10px;
    border: 1px solid {BORDER};
}}

QScrollBar:vertical {{
    background: {DARK_BG};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {ACCENT2};
    border-radius: 4px;
    min-height: 20px;
}}

QSplitter::handle {{
    background: {BORDER};
    height: 1px;
}}
"""


class ThumbLabel(QtGui.QLabel):
    """Label que muestra un thumbnail cuadrado 72×72 px."""
    SIZE = 72

    def __init__(self, url="", parent=None):
        super(ThumbLabel, self).__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet(f"background:{PANEL_BG}; border:1px solid {BORDER};")
        if url:
            self._load(url)
        else:
            self.setText("—")

    def _load(self, url):
        try:
            import urllib.request
            from io import BytesIO
            with urllib.request.urlopen(url, timeout=8) as _r:
                data = BytesIO(_r.read())
            pix = QtGui.QPixmap()
            pix.loadFromData(data.read())
            self.setPixmap(
                pix.scaled(self.SIZE, self.SIZE,
                            QtCore.Qt.KeepAspectRatio,
                            QtCore.Qt.SmoothTransformation)
            )
        except Exception:
            self.setText("?")


class VersionTableWidget(QtGui.QWidget):
    """
    Panel de selección de versiones con:
    - Filtros por Playlist, Shot, Status de entrega, texto libre
    - Vista de tabla con thumbnails
    - Selección múltiple
    """

    selection_changed = QtCore.Signal(list)  # emite lista de IDs seleccionados

    COLS = ["", "Version", "Shot", "Estado", "Entrega", "Fecha", "Método"]

    def __init__(self, sg, project_id, parent=None):
        super(VersionTableWidget, self).__init__(parent)
        self._sg = sg
        self._project_id = project_id
        self._all_versions = []
        self._filtered = []
        self._playlists = []
        self._setup_ui()
        # Carga en background — la ventana abre inmediatamente
        QtCore.QTimer.singleShot(0, self._load_all)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        main = QtGui.QVBoxLayout(self)
        main.setSpacing(8)
        main.setContentsMargins(10, 10, 10, 10)

        # ---- Barra de filtros ----
        filter_row = QtGui.QHBoxLayout()

        self.cmb_playlist = QtGui.QComboBox()
        self.cmb_playlist.setMinimumWidth(180)
        self.cmb_playlist.addItem("— Todas las playlists —", None)
        self.cmb_playlist.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(QtGui.QLabel("Playlist:"))
        filter_row.addWidget(self.cmb_playlist)

        self.cmb_status = QtGui.QComboBox()
        self.cmb_status.addItem("— Todos los estados —", None)
        self.cmb_status.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(QtGui.QLabel("Estado:"))
        filter_row.addWidget(self.cmb_status)

        self.cmb_delivery = QtGui.QComboBox()
        self.cmb_delivery.addItems([
            "— Entrega: todos —",
            "Pendiente",
            "Delivered",
        ])
        self.cmb_delivery.setCurrentIndex(1)  # Pendiente por defecto
        self.cmb_delivery.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(QtGui.QLabel("Entrega:"))
        filter_row.addWidget(self.cmb_delivery)

        self.txt_search = QtGui.QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por nombre de versión o shot…")
        self.txt_search.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.txt_search, 1)

        btn_refresh = QtGui.QPushButton("↺ Actualizar")
        btn_refresh.clicked.connect(self._load_all)
        filter_row.addWidget(btn_refresh)

        main.addLayout(filter_row)

        # ---- Segunda fila: rango temporal ----
        range_row = QtGui.QHBoxLayout()
        range_row.addWidget(QtGui.QLabel("Mostrar versiones de los últimos:"))
        self.cmb_range = QtGui.QComboBox()
        self.cmb_range.addItem("7 días",   7)
        self.cmb_range.addItem("30 días",  30)
        self.cmb_range.addItem("90 días",  90)
        self.cmb_range.addItem("6 meses",  180)
        self.cmb_range.addItem("1 año",    365)
        self.cmb_range.addItem("Todo",     None)
        self.cmb_range.setCurrentIndex(2)  # 90 días por defecto
        self.cmb_range.currentIndexChanged.connect(self._load_all)
        range_row.addWidget(self.cmb_range)
        range_row.addStretch()
        main.addLayout(range_row)

        # ---- Tabla ----
        self.table = QtGui.QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.table.setColumnWidth(0, 80)   # thumb
        self.table.setColumnWidth(2, 160)  # shot
        self.table.setColumnWidth(3, 80)   # estado (sg_status_list)
        self.table.setColumnWidth(4, 90)   # entrega
        self.table.setColumnWidth(5, 90)   # fecha
        self.table.setColumnWidth(6, 80)   # método
        self.table.itemSelectionChanged.connect(self._on_selection)
        main.addWidget(self.table)

        # ---- Overlay de carga (se muestra encima de la tabla) ----
        self._overlay = QtGui.QLabel(self.table)
        self._overlay.setAlignment(QtCore.Qt.AlignCenter)
        self._overlay.setText("⏳  Cargando versiones…")
        self._overlay.setStyleSheet(
            f"background: rgba(26,26,26,200); color: {ACCENT};"
            f"font-size: 14px; font-weight: bold; border-radius: 6px;"
        )
        self._overlay.setVisible(True)
        # El overlay se redimensiona con la tabla
        self.table.installEventFilter(self)

        # ---- Pie: nº seleccionadas ----
        footer = QtGui.QHBoxLayout()
        self.lbl_count = QtGui.QLabel("0 versiones seleccionadas")
        self.lbl_count.setStyleSheet(f"color:{TEXT_DIM};")
        footer.addWidget(self.lbl_count)
        footer.addStretch()
        btn_all = QtGui.QPushButton("Seleccionar todo")
        btn_all.clicked.connect(self.table.selectAll)
        btn_none = QtGui.QPushButton("Deseleccionar")
        btn_none.clicked.connect(self.table.clearSelection)
        footer.addWidget(btn_all)
        footer.addWidget(btn_none)
        main.addLayout(footer)

    def eventFilter(self, obj, event):
        """Mantiene el overlay centrado sobre la tabla al redimensionar."""
        if obj is self.table and event.type() == QtCore.QEvent.Resize:
            self._overlay.setGeometry(self.table.rect())
        return super(VersionTableWidget, self).eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _load_all(self):
        """Carga playlists, statuses y versiones mostrando overlay mientras trabaja."""
        self._overlay.setVisible(True)
        QtGui.QApplication.processEvents()
        try:
            self._load_playlists()
            self._load_statuses()
            self._load_versions()
        finally:
            self._overlay.setVisible(False)

    def _load_playlists(self):
        playlists = self._sg.find(
            "Playlist",
            [["project.Project.id", "is", self._project_id]],
            ["code", "id"],
            [{"field_name": "code", "direction": "asc"}],
        )
        self._playlists = playlists
        self.cmb_playlist.clear()
        self.cmb_playlist.addItem("— Todas las playlists —", None)
        for pl in playlists:
            self.cmb_playlist.addItem(pl["code"], pl["id"])

    def _load_statuses(self):
        """Carga los valores válidos del campo sg_status_list de Version desde el schema."""
        try:
            schema = self._sg.schema_field_read("Version", "sg_status_list")
            values = schema.get("sg_status_list", {}).get("properties", {}).get("valid_values", {}).get("value", [])
            self.cmb_status.clear()
            self.cmb_status.addItem("— Todos los estados —", None)
            for v in values:
                self.cmb_status.addItem(v, v)
            # Seleccionar pcl por defecto si existe
            idx = self.cmb_status.findData("pcl")
            if idx >= 0:
                self.cmb_status.setCurrentIndex(idx)
        except Exception:
            self.cmb_status.clear()
            self.cmb_status.addItem("— Todos los estados —", None)

    def _load_versions(self):
        """Carga versiones del proyecto según el rango temporal seleccionado."""
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            filters = [
                ["project.Project.id", "is", self._project_id],
            ]

            # Filtro de fecha según el combo de rango
            range_days = self.cmb_range.currentData()
            if range_days is not None:
                from datetime import datetime, timedelta
                cutoff = datetime.now() - timedelta(days=range_days)
                filters.append(["created_at", "greater_than", cutoff])

            fields = [
                "code", "id", "image",
                "entity",
                "sg_status_list",
                "sg_to_deliver___delivered",
                "sg_delivered_date",
                "sg_delivery_method_list",
                "playlists",
                "created_at",
            ]
            self._all_versions = self._sg.find(
                "Version", filters, fields,
                [{"field_name": "created_at", "direction": "desc"}],
                limit=500,
            )
            self.lbl_count.setText(
                f"0 versiones seleccionadas  ·  {len(self._all_versions)} cargadas"
            )
        finally:
            QtGui.QApplication.restoreOverrideCursor()
        self._apply_filters()

    # ------------------------------------------------------------------
    # Filtrado
    # ------------------------------------------------------------------

    def _apply_filters(self):
        pl_id = self.cmb_playlist.currentData()
        status_val = self.cmb_status.currentData()      # sg_status_list (ej: "ip", "cmpt")
        delivery_text = self.cmb_delivery.currentText() # Pendiente / Delivered
        search = self.txt_search.text().lower()

        self._filtered = []
        for v in self._all_versions:
            # Playlist
            if pl_id is not None:
                pl_ids = [p["id"] for p in (v.get("playlists") or [])]
                if pl_id not in pl_ids:
                    continue

            # Status de versión (sg_status_list)
            if status_val is not None:
                if v.get("sg_status_list") != status_val:
                    continue

            # Status de entrega
            delivered = v.get("sg_to_deliver___delivered", "")
            if delivery_text == "Pendiente" and delivered == "Delivered":
                continue
            if delivery_text == "Delivered" and delivered != "Delivered":
                continue

            # Búsqueda libre
            if search:
                name = (v.get("code") or "").lower()
                shot = (v.get("entity") or {}).get("name", "").lower()
                if search not in name and search not in shot:
                    continue

            self._filtered.append(v)

        self._populate_table()

    def _populate_table(self):
        self.table.clearContents()
        self.table.setRowCount(len(self._filtered))

        for row, v in enumerate(self._filtered):
            # Thumb
            thumb = ThumbLabel(v.get("image") or "")
            self.table.setCellWidget(row, 0, thumb)
            self.table.setRowHeight(row, ThumbLabel.SIZE + 4)

            # Nombre versión
            name_item = QtGui.QTableWidgetItem(v.get("code") or "—")
            name_item.setData(QtCore.Qt.UserRole, v["id"])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            # Shot
            entity = v.get("entity") or {}
            shot_item = QtGui.QTableWidgetItem(entity.get("name", "—"))
            shot_item.setFlags(shot_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 2, shot_item)

            # Estado (sg_status_list)
            sg_status = v.get("sg_status_list") or "—"
            sg_status_item = QtGui.QTableWidgetItem(sg_status)
            sg_status_item.setFlags(sg_status_item.flags() & ~QtCore.Qt.ItemIsEditable)
            sg_status_item.setForeground(QtGui.QColor(TEXT_DIM))
            self.table.setItem(row, 3, sg_status_item)

            # Entrega
            delivered = v.get("sg_to_deliver___delivered") or "—"
            delivered_item = QtGui.QTableWidgetItem(delivered)
            delivered_item.setFlags(delivered_item.flags() & ~QtCore.Qt.ItemIsEditable)
            if delivered == "Delivered":
                delivered_item.setForeground(QtGui.QColor(SUCCESS))
            self.table.setItem(row, 4, delivered_item)

            # Fecha
            created = v.get("created_at")
            date_str = created.strftime("%Y-%m-%d") if created else "—"
            date_item = QtGui.QTableWidgetItem(date_str)
            date_item.setFlags(date_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 5, date_item)

            # Método
            method_list = v.get("sg_delivery_method_list") or []
            method_str = ", ".join(method_list) if method_list else "—"
            method_item = QtGui.QTableWidgetItem(method_str)
            method_item.setFlags(method_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 6, method_item)

    def _on_selection(self):
        rows = set(i.row() for i in self.table.selectedItems())
        ids = []
        for r in rows:
            item = self.table.item(r, 1)
            if item:
                ids.append(item.data(QtCore.Qt.UserRole))
        self.lbl_count.setText(f"{len(ids)} versión(es) seleccionada(s)")
        self.selection_changed.emit(ids)

    def selected_ids(self):
        rows = set(i.row() for i in self.table.selectedItems())
        return [
            self.table.item(r, 1).data(QtCore.Qt.UserRole)
            for r in rows
            if self.table.item(r, 1)
        ]


# ---------------------------------------------------------------------------
# Diálogo principal
# ---------------------------------------------------------------------------

class AppDialog(QtGui.QDialog):

    def __init__(self, app, parent=None):
        super(AppDialog, self).__init__(parent)
        self._app = app
        self._sg = app.shotgun
        self._ctx = app.context
        self._worker = None
        self._selected_ids = []

        # Resolver logo según sede del proyecto — una sola query al abrir
        project_id = (self._ctx.project or {}).get("id")
        self._logo_path = resolve_logo(project_id, self._sg, self._app)

        self.setWindowTitle("EFECTOSCOPIO — Copy Version to Envios")
        self.setMinimumSize(920, 680)
        self.setStyleSheet(STYLE)

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QtGui.QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        root.addWidget(self._build_header())

        # Tabs
        self.tabs = QtGui.QTabWidget()
        self.tabs.addTab(self._build_versions_tab(), "① Versiones")
        self.tabs.addTab(self._build_delivery_tab(), "② Parámetros de entrega")
        self.tabs.addTab(self._build_progress_tab(), "③ Progreso")
        root.addWidget(self.tabs, 1)

        # Footer
        root.addWidget(self._build_footer())

    def _build_header(self):
        header = QtGui.QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background:{PANEL_BG}; border-bottom:1px solid {BORDER};")
        lay = QtGui.QHBoxLayout(header)
        lay.setContentsMargins(12, 0, 16, 0)

        # Logo según sede
        if self._logo_path and os.path.exists(self._logo_path):
            pix = QtGui.QPixmap(self._logo_path)
            lbl_logo = QtGui.QLabel()
            lbl_logo.setPixmap(pix.scaledToHeight(36, QtCore.Qt.SmoothTransformation))
            lbl_logo.setFixedWidth(pix.scaledToHeight(36).width())
            lay.addWidget(lbl_logo)
            lay.addSpacing(10)

        title = QtGui.QLabel("COPY VERSION TO ENVIOS")
        title.setStyleSheet(
            f"color:{ACCENT}; font-size:14px; font-weight:bold; letter-spacing:2px;"
        )
        lay.addWidget(title)
        lay.addStretch()

        proj_name = (self._ctx.project or {}).get("name", "—")
        lbl_proj = QtGui.QLabel(f"Proyecto: {proj_name}")
        lbl_proj.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        lay.addWidget(lbl_proj)

        return header

    def _build_versions_tab(self):
        w = QtGui.QWidget()
        lay = QtGui.QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)

        project_id = (self._ctx.project or {}).get("id")
        if project_id is None:
            lay.addWidget(QtGui.QLabel("⚠ No hay proyecto en el contexto actual."))
            return w

        self.version_panel = VersionTableWidget(self._sg, project_id)
        self.version_panel.selection_changed.connect(self._on_selection_changed)
        lay.addWidget(self.version_panel)
        return w

    def _build_delivery_tab(self):
        w = QtGui.QWidget()
        lay = QtGui.QFormLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        lay.setLabelAlignment(QtCore.Qt.AlignRight)

        def section(text):
            lbl = QtGui.QLabel(text)
            lbl.setObjectName("label_section")
            return lbl

        lay.addRow(section("DATOS DEL ENVÍO"), QtGui.QWidget())

        self.txt_title = QtGui.QLineEdit()
        self.txt_title.setPlaceholderText("Ej: Entrega VFX semana 12")
        lay.addRow("Título:", self.txt_title)

        self.txt_desc = QtGui.QTextEdit()
        self.txt_desc.setMaximumHeight(80)
        self.txt_desc.setPlaceholderText("Descripción del envío…")
        lay.addRow("Descripción:", self.txt_desc)

        self.cmb_method = QtGui.QComboBox()
        self.cmb_method.addItems([
            "ASPERA",
            "BOX",
            "CONTENT HUB",
            "DISCO DURO",
            "DROPBOX",
            "FTP CLIENTE",
            "FTP DPS",
            "MEDIA SHUTTLE",
            "FTRACK",
        ])
        lay.addRow("Método:", self.cmb_method)

        lay.addRow(section("OPCIONES"), QtGui.QWidget())

        self.chk_dailies = QtGui.QCheckBox("Incluir dailies (MOV)")
        self.chk_dailies.setChecked(False)
        lay.addRow("", self.chk_dailies)

        self.chk_22dogs = QtGui.QCheckBox(
            "Modo 22Dogs  —  estructura Comp/shot/exr + Comp/shot/mov"
        )
        self.chk_22dogs.setChecked(False)
        lay.addRow("", self.chk_22dogs)

        return w

    def _build_progress_tab(self):
        w = QtGui.QWidget()
        lay = QtGui.QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # Barra
        bar_row = QtGui.QHBoxLayout()
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.lbl_progress = QtGui.QLabel("—")
        self.lbl_progress.setStyleSheet(f"color:{TEXT_DIM};")
        bar_row.addWidget(self.progress_bar, 1)
        lay.addLayout(bar_row)
        lay.addWidget(self.lbl_progress)

        # Log
        self.log_view = QtGui.QTextEdit()
        self.log_view.setObjectName("log_view")
        self.log_view.setReadOnly(True)
        lay.addWidget(self.log_view, 1)

        return w

    def _build_footer(self):
        footer = QtGui.QWidget()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            f"background:{PANEL_BG}; border-top:1px solid {BORDER};"
        )
        lay = QtGui.QHBoxLayout(footer)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        self.lbl_sel = QtGui.QLabel("0 versiones seleccionadas")
        self.lbl_sel.setStyleSheet(f"color:{TEXT_DIM};")
        lay.addWidget(self.lbl_sel)

        lay.addStretch()

        self.btn_cancel = QtGui.QPushButton("Cancelar copia")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_worker)
        lay.addWidget(self.btn_cancel)

        self.btn_run = QtGui.QPushButton("▶  Iniciar copia")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._start_copy)
        lay.addWidget(self.btn_run)

        return footer

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_selection_changed(self, ids):
        self._selected_ids = ids
        n = len(ids)
        self.lbl_sel.setText(
            f"{n} versión(es) seleccionada(s)"
        )
        self.btn_run.setEnabled(n > 0)

    def _start_copy(self):
        if not self._selected_ids:
            QtGui.QMessageBox.warning(self, "Sin selección",
                                      "Selecciona al menos una versión.")
            return

        title = self.txt_title.text().strip()
        if not title:
            QtGui.QMessageBox.warning(self, "Título requerido",
                                      "Introduce un título para el envío.")
            return

        # Confirmar
        n = len(self._selected_ids)
        mode_txt = "22Dogs" if self.chk_22dogs.isChecked() else "Estándar"
        reply = QtGui.QMessageBox.question(
            self,
            "Confirmar copia",
            f"Se copiarán {n} versión(es) en modo {mode_txt}.\n\n¿Continuar?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
        )
        if reply != QtGui.QMessageBox.Yes:
            return

        # Cambiar a pestaña progreso
        self.tabs.setCurrentIndex(2)
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Iniciando…")
        self.btn_run.setEnabled(False)
        self.btn_cancel.setVisible(True)

        # Logo: ya resuelto en __init__ según sede del proyecto
        logo = self._logo_path

        self._worker = CopyWorker(
            sg=self._sg,
            project=self._ctx.project,
            version_ids=self._selected_ids,
            title=title,
            description=self.txt_desc.toPlainText(),
            method=self.cmb_method.currentText(),
            include_dailies=self.chk_dailies.isChecked(),
            mode_22dogs=self.chk_22dogs.isChecked(),
            logo_path=logo,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel_worker(self):
        if self._worker:
            self._worker.abort()
            self._on_log("⚠ Cancelando…")

    def _on_progress(self, current, total, desc):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_progress.setText(desc)

    def _on_log(self, line):
        self.log_view.append(line)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished(self, success, msg):
        self.btn_cancel.setVisible(False)
        self.btn_run.setEnabled(True)
        self._on_log(f"\n{'✔' if success else '✘'} {msg}")
        self.lbl_progress.setText(msg)

        if success:
            QtGui.QMessageBox.information(self, "Completado", msg)
        else:
            QtGui.QMessageBox.critical(self, "Error", msg)

        self._worker = None