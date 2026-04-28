#!/usr/bin/env python3
"""
RHEL Repository Viewer
A PyQt6 desktop app to parse .repo files and list packages,
with support for $releasever and $basearch variable substitution.
"""

import sys
import os
import re
import configparser
import urllib.request
import urllib.error
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextEdit, QSplitter, QFrame,
    QStatusBar, QHeaderView, QComboBox, QGroupBox, QProgressBar,
    QMessageBox, QTreeWidget, QTreeWidgetItem, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter,
    QLinearGradient, QBrush, QFontDatabase, QDragEnterEvent, QDropEvent
)


# ── Palette ────────────────────────────────────────────────────────────────
DARK_BG      = "#0d1117"
PANEL_BG     = "#161b22"
BORDER       = "#30363d"
ACCENT_RED   = "#e03c3c"
ACCENT_AMBER = "#f0a030"
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED   = "#8b949e"
INPUT_BG     = "#21262d"
SUCCESS      = "#3fb950"
WARNING      = "#d29922"

QSS = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 8px;
    padding: 8px 4px 4px 4px;
    background-color: {PANEL_BG};
    font-weight: bold;
    color: {TEXT_MUTED};
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QLineEdit {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {ACCENT_RED};
}}
QLineEdit:hover {{
    border-color: #484f58;
}}

QPushButton {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 16px;
    color: {TEXT_PRIMARY};
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{
    background-color: #2d333b;
    border-color: #484f58;
}}
QPushButton:pressed {{
    background-color: #22272e;
}}
QPushButton#primary {{
    background-color: {ACCENT_RED};
    border-color: {ACCENT_RED};
    color: white;
}}
QPushButton#primary:hover {{
    background-color: #c43030;
    border-color: #c43030;
}}
QPushButton#primary:pressed {{
    background-color: #a82828;
}}
QPushButton#secondary {{
    background-color: transparent;
    border-color: {ACCENT_AMBER};
    color: {ACCENT_AMBER};
}}
QPushButton#secondary:hover {{
    background-color: rgba(240,160,48,0.1);
}}

QTableWidget {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    gridline-color: {BORDER};
    color: {TEXT_PRIMARY};
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: rgba(224,60,60,0.25);
    color: {TEXT_PRIMARY};
}}
QTableWidget::item:alternate {{
    background-color: rgba(255,255,255,0.02);
}}
QHeaderView::section {{
    background-color: {INPUT_BG};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {PANEL_BG};
}}
QTabBar::tab {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 7px 18px;
    color: {TEXT_MUTED};
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-size: 12px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background-color: {PANEL_BG};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT_RED};
}}
QTabBar::tab:hover:!selected {{
    background-color: #2d333b;
    color: {TEXT_PRIMARY};
}}

QTextEdit {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px;
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.5;
}}

QTreeWidget {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    alternate-background-color: rgba(255,255,255,0.02);
}}
QTreeWidget::item {{
    padding: 3px 4px;
}}
QTreeWidget::item:selected {{
    background-color: rgba(224,60,60,0.25);
    color: {TEXT_PRIMARY};
}}
QTreeWidget::item:hover {{
    background-color: rgba(255,255,255,0.05);
}}
QTreeWidget QHeaderView::section {{
    background-color: {INPUT_BG};
}}

QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {INPUT_BG};
    text-align: center;
    color: {TEXT_PRIMARY};
    font-size: 11px;
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_RED};
    border-radius: 2px;
}}

QStatusBar {{
    background-color: {PANEL_BG};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
    font-size: 11px;
    padding: 2px 8px;
}}

QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
    height: 1px;
}}

QScrollBar:vertical {{
    background: {PANEL_BG};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: #484f58;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {PANEL_BG};
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #484f58;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QLabel#title {{
    font-size: 20px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    letter-spacing: 1px;
}}
QLabel#subtitle {{
    font-size: 11px;
    color: {TEXT_MUTED};
    letter-spacing: 2px;
}}
QLabel#badge {{
    background-color: {ACCENT_RED};
    color: white;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QLabel#section_label {{
    color: {TEXT_MUTED};
    font-size: 11px;
    letter-spacing: 1px;
    font-weight: bold;
}}
QLabel#url_label {{
    color: {ACCENT_AMBER};
    font-size: 11px;
}}
QComboBox {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 10px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    min-width: 80px;
}}
QComboBox:focus {{
    border-color: {ACCENT_RED};
}}
QComboBox QAbstractItemView {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
    selection-background-color: rgba(224,60,60,0.3);
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
"""


# ── Repo Parser ─────────────────────────────────────────────────────────────
class RepoParser:
    """Parse .repo files and substitute $releasever / $basearch."""

    KNOWN_BASEARCH = ["x86_64", "aarch64", "ppc64le", "s390x", "i686"]
    KNOWN_VERSIONS = ["7", "8", "9", "10"]

    @staticmethod
    def substitute(text: str, releasever: str, basearch: str) -> str:
        text = text.replace("$releasever", releasever)
        text = text.replace("${releasever}", releasever)
        text = text.replace("$basearch", basearch)
        text = text.replace("${basearch}", basearch)
        return text

    @staticmethod
    def parse_file(path: str, releasever: str, basearch: str) -> list[dict]:
        """Return list of repo dicts with substituted URLs."""
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
        # substitute before parsing so configparser sees real values
        substituted = RepoParser.substitute(raw, releasever, basearch)

        cfg = configparser.RawConfigParser()
        cfg.read_string(substituted)

        repos = []
        for section in cfg.sections():
            repo = {"id": section}
            for key in ("name", "baseurl", "mirrorlist", "metalink",
                        "enabled", "gpgcheck", "gpgkey", "metadata_expire",
                        "type", "skip_if_unavailable"):
                repo[key] = cfg.get(section, key, fallback="")
            # detect whether variables remain un-substituted
            combined = " ".join(repo.values())
            repo["has_unresolved"] = bool(
                re.search(r'\$\w+|\$\{[^}]+\}', combined)
            )
            repos.append(repo)
        return repos


# ── Worker Thread ────────────────────────────────────────────────────────────
class FetchWorker(QThread):
    progress      = pyqtSignal(int, str)          # percent, message
    repo_done     = pyqtSignal(str, list)         # repo_id, packages
    repo_error    = pyqtSignal(str, str)          # repo_id, error
    finished_all  = pyqtSignal()

    def __init__(self, repos: list[dict]):
        super().__init__()
        self.repos   = repos
        self._abort  = False

    def abort(self):
        self._abort = True

    def run(self):
        total = len(self.repos)
        for i, repo in enumerate(self.repos):
            if self._abort:
                break
            repo_id = repo["id"]
            pct = int((i / total) * 100)
            self.progress.emit(pct, f"Fetching metadata: {repo_id}")

            url = repo.get("baseurl") or repo.get("mirrorlist") or ""
            if not url:
                self.repo_error.emit(repo_id, "No baseurl or mirrorlist configured")
                continue

            # Only attempt baseurl (mirrorlist handling is simplistic here)
            baseurl = url.split("\n")[0].strip().rstrip("/")
            packages = self._fetch_repomd(baseurl, repo_id)
            if isinstance(packages, str):
                self.repo_error.emit(repo_id, packages)
            else:
                self.repo_done.emit(repo_id, packages)

        self.progress.emit(100, "Done")
        self.finished_all.emit()

    def _fetch_repomd(self, baseurl: str, repo_id: str):
        """Fetch repomd.xml → primary.xml.gz → package list."""
        try:
            repomd_url = f"{baseurl}/repodata/repomd.xml"
            data = self._get(repomd_url)
            primary_href = self._parse_repomd(data)
            if not primary_href:
                return "Could not locate primary metadata in repomd.xml"
            primary_url = f"{baseurl}/{primary_href}"
            gz_data = self._get(primary_url)
            xml_data = gzip.decompress(gz_data)
            return self._parse_primary(xml_data)
        except urllib.error.HTTPError as e:
            return f"HTTP {e.code}: {e.reason} — {repomd_url if 'repomd_url' in dir() else baseurl}"
        except urllib.error.URLError as e:
            return f"Connection error: {e.reason}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def _get(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "RepoViewer/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()

    @staticmethod
    def _parse_repomd(data: bytes) -> str | None:
        NS = {"r": "http://linux.duke.edu/metadata/repo"}
        root = ET.fromstring(data)
        for dtype in ("primary",):
            el = root.find(f".//r:data[@type='{dtype}']/r:location", NS)
            if el is not None:
                return el.get("href", "")
        # fallback without namespace
        for el in root.iter("location"):
            return el.get("href", "")
        return None

    @staticmethod
    def _parse_primary(data: bytes) -> list[dict]:
        NS = {
            "r": "http://linux.duke.edu/metadata/common",
            "rpm": "http://linux.duke.edu/metadata/rpm",
        }
        root = ET.fromstring(data)
        packages = []
        for pkg in root.findall("r:package", NS):
            name    = pkg.findtext("r:name", "", NS)
            arch    = pkg.findtext("r:arch", "", NS)
            summary = pkg.findtext("r:summary", "", NS)
            ver_el  = pkg.find("r:version", NS)
            epoch   = ver_el.get("epoch", "0") if ver_el is not None else "0"
            ver     = ver_el.get("ver", "")    if ver_el is not None else ""
            rel     = ver_el.get("rel", "")    if ver_el is not None else ""
            size_el = pkg.find("r:size", NS)
            size    = size_el.get("package", "0") if size_el is not None else "0"
            packages.append({
                "name": name, "arch": arch,
                "epoch": epoch, "version": ver, "release": rel,
                "summary": summary, "size": size,
            })
        return packages


# ── Drop Zone ────────────────────────────────────────────────────────────────
class DropZone(QFrame):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(72)
        self.setMaximumHeight(90)
        self._active = False
        self._path   = ""
        self.setObjectName("drop_zone")
        self.setStyleSheet(f"""
            QFrame#drop_zone {{
                border: 2px dashed {BORDER};
                border-radius: 8px;
                background: {PANEL_BG};
            }}
        """)

        layout = QHBoxLayout(self)
        self._icon  = QLabel("⬇")
        self._icon.setFont(QFont("monospace", 22))
        self._icon.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        self._label = QLabel("Drop a .repo file here — or click Browse")
        self._label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; border: none;")
        layout.addStretch()
        layout.addWidget(self._icon)
        layout.addSpacing(10)
        layout.addWidget(self._label)
        layout.addStretch()

    def set_path(self, path: str):
        self._path = path
        filename = os.path.basename(path)
        self._label.setText(f"  {filename}")
        self._label.setStyleSheet(f"color: {SUCCESS}; font-size: 13px; font-weight: bold; border: none;")
        self._icon.setText("✓")
        self._icon.setStyleSheet(f"color: {SUCCESS}; border: none;")
        self.setStyleSheet(f"""
            QFrame#drop_zone {{
                border: 2px dashed {SUCCESS};
                border-radius: 8px;
                background: rgba(63,185,80,0.05);
            }}
        """)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            url = e.mimeData().urls()[0].toLocalFile()
            if url.endswith(".repo"):
                e.acceptProposedAction()
                self.setStyleSheet(f"""
                    QFrame#drop_zone {{
                        border: 2px dashed {ACCENT_RED};
                        border-radius: 8px;
                        background: rgba(224,60,60,0.08);
                    }}
                """)

    def dragLeaveEvent(self, e):
        self.setStyleSheet(f"""
            QFrame#drop_zone {{
                border: 2px dashed {BORDER};
                border-radius: 8px;
                background: {PANEL_BG};
            }}
        """)

    def dropEvent(self, e: QDropEvent):
        url = e.mimeData().urls()[0].toLocalFile()
        if url.endswith(".repo"):
            self.set_path(url)
            self.file_dropped.emit(url)


# ── Main Window ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RHEL Repo Viewer")
        self.setMinimumSize(1100, 720)
        self.repos: list[dict] = []
        self.current_file = ""
        self._worker: FetchWorker | None = None
        self._pkg_data: dict[str, list[dict]] = {}   # repo_id → packages
        self._build_ui()
        self.setStyleSheet(QSS)

    # ── UI Construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 12, 16, 12)
        body_layout.setSpacing(10)

        body_layout.addWidget(self._make_file_row())
        body_layout.addWidget(self._make_vars_row())
        body_layout.addWidget(self._make_tabs())

        root.addWidget(body, 1)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._status_label = QLabel("Ready — load a .repo file to begin")
        self._status_label.setStyleSheet(f"color: {TEXT_MUTED};")
        self.status.addWidget(self._status_label, 1)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(180)
        self._progress.setVisible(False)
        self.status.addPermanentWidget(self._progress)

    def _make_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(58)
        hdr.setStyleSheet(f"""
            background-color: {PANEL_BG};
            border-bottom: 1px solid {BORDER};
        """)
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(18, 0, 18, 0)

        # red square logo
        logo = QLabel("▣")
        logo.setFont(QFont("monospace", 22))
        logo.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold;")

        title = QLabel("REPO<span style='color:{ACCENT_RED}'>VIEWER</span>")
        title.setFont(QFont("Consolas", 17, QFont.Weight.Bold))
        title.setObjectName("title")
        title.setTextFormat(Qt.TextFormat.RichText)

        sub = QLabel("RHEL REPOSITORY EXPLORER")
        sub.setObjectName("subtitle")

        lay.addWidget(logo)
        lay.addSpacing(10)
        lay.addWidget(title)
        lay.addSpacing(14)
        lay.addWidget(sub, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch()

        self._pkg_count_badge = QLabel("0 repos")
        self._pkg_count_badge.setObjectName("badge")
        lay.addWidget(self._pkg_count_badge)

        return hdr

    def _make_file_row(self) -> QGroupBox:
        box = QGroupBox("Repository File")
        lay = QHBoxLayout(box)
        lay.setSpacing(8)

        self._drop = DropZone()
        self._drop.file_dropped.connect(self._load_file)
        lay.addWidget(self._drop, 1)

        btn_browse = QPushButton("Browse…")
        btn_browse.setObjectName("secondary")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse)
        lay.addWidget(btn_browse)

        btn_reload = QPushButton("↺  Reload")
        btn_reload.setFixedWidth(90)
        btn_reload.clicked.connect(self._reload)
        lay.addWidget(btn_reload)

        return box

    def _make_vars_row(self) -> QGroupBox:
        box = QGroupBox("Variable Substitution")
        lay = QHBoxLayout(box)
        lay.setSpacing(12)

        # releasever
        lay.addWidget(QLabel("$releasever"))
        self._rel_edit = QLineEdit("9")
        self._rel_edit.setFixedWidth(80)
        self._rel_edit.setPlaceholderText("e.g. 9")
        lay.addWidget(self._rel_edit)

        # quick pick
        self._rel_combo = QComboBox()
        self._rel_combo.addItems(RepoParser.KNOWN_VERSIONS)
        self._rel_combo.setCurrentText("9")
        self._rel_combo.currentTextChanged.connect(self._rel_edit.setText)
        lay.addWidget(self._rel_combo)

        lay.addSpacing(20)

        # basearch
        lay.addWidget(QLabel("$basearch"))
        self._arch_edit = QLineEdit("x86_64")
        self._arch_edit.setFixedWidth(110)
        self._arch_edit.setPlaceholderText("e.g. x86_64")
        lay.addWidget(self._arch_edit)

        self._arch_combo = QComboBox()
        self._arch_combo.addItems(RepoParser.KNOWN_BASEARCH)
        self._arch_combo.currentTextChanged.connect(self._arch_edit.setText)
        lay.addWidget(self._arch_combo)

        lay.addStretch()

        btn_apply = QPushButton("Apply Variables")
        btn_apply.setObjectName("primary")
        btn_apply.clicked.connect(self._reload)
        lay.addWidget(btn_apply)

        btn_fetch = QPushButton("⬇  Fetch Packages")
        btn_fetch.setObjectName("secondary")
        btn_fetch.clicked.connect(self._fetch_packages)
        lay.addWidget(btn_fetch)

        btn_abort = QPushButton("■  Stop")
        btn_abort.clicked.connect(self._abort_fetch)
        self._btn_abort = btn_abort
        btn_abort.setVisible(False)
        lay.addWidget(btn_abort)

        return box

    def _make_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()

        # Tab 1 — Repos
        self._tabs.addTab(self._make_repos_tab(), "Repositories")
        # Tab 2 — Packages
        self._tabs.addTab(self._make_packages_tab(), "Packages")
        # Tab 3 — Raw
        self._tabs.addTab(self._make_raw_tab(), "Raw File")

        return self._tabs

    def _make_repos_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 8, 4, 4)

        self._repo_table = QTableWidget()
        self._repo_table.setColumnCount(7)
        self._repo_table.setHorizontalHeaderLabels([
            "ID", "Name", "Enabled", "GPG Check", "Base URL / Mirrorlist", "Metadata Expire", "Warnings"
        ])
        self._repo_table.setAlternatingRowColors(True)
        self._repo_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._repo_table.setSortingEnabled(True)
        self._repo_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._repo_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._repo_table.verticalHeader().setVisible(False)
        self._repo_table.setShowGrid(False)
        lay.addWidget(self._repo_table)
        return w

    def _make_packages_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 8, 4, 4)

        # filter bar
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self._pkg_filter = QLineEdit()
        self._pkg_filter.setPlaceholderText("Search packages…")
        self._pkg_filter.textChanged.connect(self._filter_packages)
        filter_row.addWidget(self._pkg_filter, 1)
        lay.addLayout(filter_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # left: tree by repo
        self._pkg_tree = QTreeWidget()
        self._pkg_tree.setHeaderLabels(["Repository / Package", "Arch", "Version", "Size"])
        self._pkg_tree.setAlternatingRowColors(True)
        self._pkg_tree.itemSelectionChanged.connect(self._pkg_selected)
        splitter.addWidget(self._pkg_tree)

        # right: detail
        detail_w = QWidget()
        detail_lay = QVBoxLayout(detail_w)
        detail_lay.setContentsMargins(4, 0, 0, 0)
        detail_lay.addWidget(QLabel("Package Details", objectName="section_label"))
        self._pkg_detail = QTextEdit()
        self._pkg_detail.setReadOnly(True)
        self._pkg_detail.setPlaceholderText("Select a package to see details…")
        detail_lay.addWidget(self._pkg_detail)
        splitter.addWidget(detail_w)

        splitter.setSizes([650, 350])
        lay.addWidget(splitter, 1)

        return w

    def _make_raw_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 8, 4, 4)

        hbar = QHBoxLayout()
        hbar.addWidget(QLabel("Showing:", objectName="section_label"))
        self._raw_mode = QComboBox()
        self._raw_mode.addItems(["Original", "After Variable Substitution"])
        self._raw_mode.currentIndexChanged.connect(self._update_raw)
        hbar.addWidget(self._raw_mode)
        hbar.addStretch()
        lay.addLayout(hbar)

        self._raw_view = QTextEdit()
        self._raw_view.setReadOnly(True)
        self._raw_view.setFont(QFont("Consolas", 12))
        lay.addWidget(self._raw_view, 1)
        return w

    # ── Logic ────────────────────────────────────────────────────────────────
    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open .repo file", str(Path.home()),
            "Repo files (*.repo);;All files (*)"
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self.current_file = path
        self._drop.set_path(path)
        self._parse_repos()
        self._update_raw()
        self._tabs.setCurrentIndex(0)

    def _reload(self):
        if self.current_file:
            self._parse_repos()
            self._update_raw()

    def _parse_repos(self):
        if not self.current_file:
            return
        releasever = self._rel_edit.text().strip() or "9"
        basearch   = self._arch_edit.text().strip() or "x86_64"
        try:
            self.repos = RepoParser.parse_file(self.current_file, releasever, basearch)
        except Exception as e:
            QMessageBox.critical(self, "Parse Error", str(e))
            return
        self._populate_repo_table()
        self._pkg_count_badge.setText(f"{len(self.repos)} repo{'s' if len(self.repos)!=1 else ''}")
        self._set_status(f"Loaded {len(self.repos)} repositories from {os.path.basename(self.current_file)}", SUCCESS)

    def _populate_repo_table(self):
        t = self._repo_table
        t.setSortingEnabled(False)
        t.setRowCount(len(self.repos))
        for row, repo in enumerate(self.repos):
            url = repo.get("baseurl") or repo.get("mirrorlist") or repo.get("metalink") or "—"
            warn = "⚠ unresolved vars" if repo["has_unresolved"] else ""

            def cell(text, color=None):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if color:
                    item.setForeground(QColor(color))
                return item

            t.setItem(row, 0, cell(repo["id"], ACCENT_AMBER))
            t.setItem(row, 1, cell(repo.get("name", "")))
            enabled = repo.get("enabled", "1")
            t.setItem(row, 2, cell("Yes" if enabled != "0" else "No",
                                   SUCCESS if enabled != "0" else TEXT_MUTED))
            gpg = repo.get("gpgcheck", "")
            t.setItem(row, 3, cell("Yes" if gpg == "1" else "No",
                                   SUCCESS if gpg == "1" else WARNING))
            t.setItem(row, 4, cell(url))
            t.setItem(row, 5, cell(repo.get("metadata_expire", "")))
            t.setItem(row, 6, cell(warn, WARNING))
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def _update_raw(self):
        if not self.current_file:
            return
        raw = Path(self.current_file).read_text(errors="replace")
        if self._raw_mode.currentIndex() == 1:
            rv = self._rel_edit.text().strip() or "9"
            ba = self._arch_edit.text().strip() or "x86_64"
            raw = RepoParser.substitute(raw, rv, ba)
        self._raw_view.setPlainText(raw)

    # ── Package fetching ─────────────────────────────────────────────────────
    def _fetch_packages(self):
        if not self.repos:
            QMessageBox.information(self, "No repos", "Load a .repo file first.")
            return
        if self._worker and self._worker.isRunning():
            return
        self._pkg_data.clear()
        self._pkg_tree.clear()
        self._pkg_detail.clear()
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._btn_abort.setVisible(True)
        self._set_status("Fetching package metadata…", ACCENT_AMBER)

        # enabled repos only
        enabled = [r for r in self.repos if r.get("enabled", "1") != "0"]
        self._worker = FetchWorker(enabled)
        self._worker.progress.connect(self._on_progress)
        self._worker.repo_done.connect(self._on_repo_done)
        self._worker.repo_error.connect(self._on_repo_error)
        self._worker.finished_all.connect(self._on_fetch_done)
        self._worker.start()

    def _abort_fetch(self):
        if self._worker:
            self._worker.abort()

    def _on_progress(self, pct: int, msg: str):
        self._progress.setValue(pct)
        self._set_status(msg, ACCENT_AMBER)

    def _on_repo_done(self, repo_id: str, packages: list):
        self._pkg_data[repo_id] = packages
        self._add_repo_tree_node(repo_id, packages)
        self._tabs.setCurrentIndex(1)

    def _on_repo_error(self, repo_id: str, error: str):
        root = QTreeWidgetItem(self._pkg_tree, [repo_id, "", "ERROR", ""])
        root.setForeground(0, QColor(ACCENT_RED))
        err_item = QTreeWidgetItem(root, [error, "", "", ""])
        err_item.setForeground(0, QColor(TEXT_MUTED))
        root.setExpanded(True)

    def _on_fetch_done(self):
        self._progress.setVisible(False)
        self._btn_abort.setVisible(False)
        total = sum(len(v) for v in self._pkg_data.values())
        self._set_status(
            f"Fetched {total:,} packages across {len(self._pkg_data)} repos",
            SUCCESS
        )

    def _add_repo_tree_node(self, repo_id: str, packages: list[dict]):
        repo_label = f"{repo_id}  ({len(packages):,} packages)"
        root = QTreeWidgetItem(self._pkg_tree, [repo_label, "", "", ""])
        root.setForeground(0, QColor(ACCENT_AMBER))
        root.setFont(0, QFont("Consolas", 12, QFont.Weight.Bold))
        root.setData(0, Qt.ItemDataRole.UserRole, {"_type": "repo", "repo_id": repo_id})

        for pkg in packages[:500]:   # cap at 500 per repo for UI performance
            size_kb = int(pkg.get("size", 0)) // 1024
            ver_str = f"{pkg['version']}-{pkg['release']}"
            item = QTreeWidgetItem(root, [
                pkg["name"], pkg["arch"], ver_str,
                f"{size_kb:,} KB" if size_kb else ""
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, pkg)
        root.setExpanded(False)

        if len(packages) > 500:
            note = QTreeWidgetItem(root, [
                f"… and {len(packages)-500:,} more (filter to narrow)", "", "", ""
            ])
            note.setForeground(0, QColor(TEXT_MUTED))

    def _pkg_selected(self):
        items = self._pkg_tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not data or "_type" in data:
            return
        pkg = data
        epoch = f":{pkg['epoch']}" if pkg.get("epoch", "0") not in ("", "0") else ""
        evr   = f"{epoch}{pkg['version']}-{pkg['release']}"
        size_kb = int(pkg.get("size", 0)) // 1024
        html = f"""<style>
            body {{ color: #e6edf3; font-family: Consolas,monospace; font-size:12px; }}
            .key {{ color: #8b949e; }}
            .val {{ color: #e6edf3; }}
            .name {{ color: #f0a030; font-size:15px; font-weight:bold; }}
            .evr  {{ color: #e03c3c; }}
        </style>
        <p class='name'>{pkg['name']}</p>
        <p class='evr'>{evr}</p>
        <br>
        <table cellspacing='4'>
        <tr><td class='key'>Architecture</td><td>&nbsp;</td><td class='val'>{pkg.get('arch','')}</td></tr>
        <tr><td class='key'>Version</td><td></td><td class='val'>{pkg.get('version','')}</td></tr>
        <tr><td class='key'>Release</td><td></td><td class='val'>{pkg.get('release','')}</td></tr>
        <tr><td class='key'>Epoch</td><td></td><td class='val'>{pkg.get('epoch','0')}</td></tr>
        <tr><td class='key'>Package Size</td><td></td><td class='val'>{size_kb:,} KB</td></tr>
        <tr><td class='key'>Summary</td><td></td><td class='val'>{pkg.get('summary','')}</td></tr>
        </table>"""
        self._pkg_detail.setHtml(html)

    def _filter_packages(self, text: str):
        text = text.lower()
        for i in range(self._pkg_tree.topLevelItemCount()):
            repo_item = self._pkg_tree.topLevelItem(i)
            visible_count = 0
            for j in range(repo_item.childCount()):
                pkg_item = repo_item.child(j)
                name = pkg_item.text(0).lower()
                match = text in name
                pkg_item.setHidden(not match)
                if match:
                    visible_count += 1
            if text:
                repo_item.setExpanded(True)

    def _set_status(self, msg: str, color: str = TEXT_MUTED):
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {color};")


# ── Entry point ──────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RHEL Repo Viewer")
    app.setApplicationVersion("1.0")

    # try to set a nice app icon using a painted pixmap
    pix = QPixmap(48, 48)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(ACCENT_RED)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 40, 40, 8, 8)
    p.setPen(QColor("white"))
    p.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "▣")
    p.end()
    app.setWindowIcon(QIcon(pix))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
