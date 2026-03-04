import sys
import os
import re
import shutil
import json
import base64
import traceback
import subprocess
import platform
import random
import time
from pathlib import Path
from collections import deque
from datetime import datetime

# --- ИМПОРТЫ ДЛЯ СТАРЫХ .DOC ФАЙЛОВ (Windows) ---
try:
    import win32com.client
    import pythoncom
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("ВНИМАНИЕ: Для чтения старых .doc установите pywin32: pip install pywin32")

# --- ИМПОРТЫ ДЛЯ OCR ---
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

import docx
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog,
    QStatusBar, QSplitter, QMenu, QListWidget, QListWidgetItem,
    QCompleter, QStackedWidget, QTextEdit, QPlainTextEdit, QDialog,
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QMessageBox, QSlider,
    QTabWidget, QFrame, QGridLayout, QScrollArea, QDialogButtonBox,
    QAbstractItemView, QTimeEdit, QDateTimeEdit, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QByteArray, QTimer,
    QStringListModel, QObject, QUrl, QTime, QDate, QDateTime
)
from PyQt6.QtGui import (
    QAction, QCursor, QIcon, QPixmap, QTextOption,
    QTextCursor, QColor, QIntValidator, QDesktopServices,
    QPainter, QPen, QBrush, QFont
)

from whoosh.index import create_in, open_dir, EmptyIndexError
from whoosh.fields import Schema, TEXT, ID, NUMERIC, DATETIME
from whoosh.analysis import LanguageAnalyzer
from whoosh.qparser import MultifieldParser, PhrasePlugin
from whoosh.highlight import HtmlFormatter, ContextFragmenter
from whoosh.query import Or, Term, FuzzyTerm


# --- ПУТИ ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

INDEX_DIR = BASE_DIR / "search_index"
CONFIG_FILE = BASE_DIR / "config.json"

ALL_SUPPORTED_EXTS = [".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".bmp"]

# --- КОНСТАНТЫ И ИСКЛЮЧЕНИЯ ---
class SearchServiceError(Exception): pass
class IndexNotFoundError(SearchServiceError): pass

# --- ИКОНКИ (Base64) ---
SEARCH_ICON_DARK_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2UwZTBlMCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxjaXJjbGUgY3g9IjExIiBjeT0iMTEiIHI9IjgiLz48cGF0aCBkPSJtMjEgMjEtNC4zLTQuMyIvPjwvc3ZnPg=="
SEARCH_ICON_LIGHT_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzVENDAzNyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxjaXJjbGUgY3g9IjExIiBjeT0iMTEiIHI9IjgiLz48cGF0aCBkPSJtMjEgMjEtNC4zLTQuMyIvPjwvc3ZnPg=="
SUN_ICON_DARK_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNlMGUwZTAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSI1Ij48L2NpcmNsZT48bGluZSB4MT0iMTIiIHkxPSIxIiB4Mj0iMTIiIHkyPSIzIj48L2xpbmU+PGxpbmUgeDE9IjEyIiB5MT0iMjEiIHgyPSIxMiIgeTI9IjIzIj48L2xpbmU+PGxpbmUgeDE9IjQuMjIiIHkxPSI0LjIyIiB4Mj0iNS42NCIgeTI9IjUuNjQiPjwvbGluZT48bGluZSB4MT0iMTguMzYiIHkxPSIxOC4zNiIgeDI9IjE5Ljc4IiB5Mj0iMTkuNzgiPjwvbGluZT48bGluZSB4MT0iMSIgeTE9IjEyIiB4Mj0iMyIgeTI9IjEyIj48L2xpbmU+PGxpbmUgeDE9IjIxIiB5MT0iMTIiIHgyPSIyMyIgeTI9IjEyIj48L2xpbmU+PGxpbmUgeDE9IjQuMjIiIHkxPSIxOS43OCIgeDI9IjUuNjQiIHkyPSIxOC4zNiI+PC9saW5lPjxsaW5lIHgxPSIxOC4zNiIgeTE9IjUuNjQiIHgyPSIxOS43OCIgeTI9IjQuMjIiPjwvbGluZT48L3N2Zz4="
MOON_ICON_LIGHT_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzVENDAzNyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xMiAzYTkgOSAwIDEgMCA4Ljc5MSA5LjMyNEE3IDcgMCAxIDEgMTIgM3oiLz48L3N2Zz4="
SETTINGS_ICON_DARK_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiB2aWV3Qm94PSIyIDIgMjggMjgiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2UwZTBlMCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xOS4xOSAzLjc1N0ExIDEgMCAwMDE4LjIyIDNoLTQuNDRhMSAxIDAgMDAtLjk3Ljc1N2wtLjY2IDIuNjQ0YTEgMSAwIDAxLS40Ny42MjNsLTEuMjkxLjc0N2ExIDEgMCAwMS0uNzc2LjA5NWwtMi42Mi0uNzVhMSAxIDAgMDAtMS4xNDIuNDYybC0yLjIxOSAzLjg0NGExIDEgMCAwMC4xNzEgMS4yMTlsMS45NiAxLjg5NWExIDEgMCAwMS4zMDUuNzE5djEuNDlhMSAxIDAgMDEtLjMwNS43MmwtMS45NiAxLjg5NGExIDEgMCAwMC0uMTcgMS4yMmwyLjIxOCAzLjg0M2ExIDEgMCAwMDEuMTQxLjQ2MWwyLjYxLS43NDZhMSAxIDAgMDEuNzkzLjEwNmwuOTYzLjU4NGExIDEgMCAwMS40My41NGwuOTg0IDIuOTVhMSAxIDAgMDAuOTQ5LjY4M2g0LjU1OGExIDEgMCAwMC45NDktLjY4NGwuOTgyLTIuOTQ3YTEgMSAwIDAxLjQzNS0uNTQybC45ODItLjU4N2ExIDEgMCAwMS43OS0uMTAzbDIuNTkuNzQ1YTEgMSAwIDAwMS4xNDItLjQ2MWwyLjIyMi0zLjg0OGExIDEgMCAwMC0uMTY2LTEuMjE0bC0xLjkzMy0xLjg5NmExIDEgMCAwMS0uMy0uNzEzdi0xLjVhMSAxIDAgMDEuMy0uNzEzbDEuOTMzLTEuODk2YTEgMSAwIDAwLjE2Ni0xLjIxNGwtMi4yMjItMy44NDhhMSAxIDAgMDAtMS4xNDItLjQ2bC0yLjYuNzQ3YTEgMSAwIDAxLS43NzQtLjA5M2wtMS4zMS0uNzVhMSAxIDAgMDEtLjQ3NC0uNjI1bC0uNjYtMi42NHoiLz48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSI1Ii8+PC9zdmc+"
SETTINGS_ICON_LIGHT_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiB2aWV3Qm94PSIyIDIgMjggMjgiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzVENDAzNyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xOS4xOSAzLjc1N0ExIDEgMCAwMDE4LjIyIDNoLTQuNDRhMSAxIDAgMDAtLjk3Ljc1N2wtLjY2IDIuNjQ0YTEgMSAwIDAxLS40Ny42MjNsLTEuMjkxLjc0N2ExIDEgMCAwMS0uNzc2LjA5NWwtMi42Mi0uNzVhMSAxIDAgMDAtMS4xNDIuNDYybC0yLjIxOSAzLjg0NGExIDEgMCAwMC4xNzEgMS4yMTlsMS45NiAxLjg5NWExIDEgMCAwMS4zMDUuNzE5djEuNDlhMSAxIDAgMDEtLjMwNS43MmwtMS45NiAxLjg5NGExIDEgMCAwMC0uMTcgMS4yMmwyLjIxOCAzLjg0M2ExIDEgMCAwMDEuMTQxLjQ2MWwyLjYxLS43NDZhMSAxIDAgMDEuNzkzLjEwNmwuOTYzLjU4NGExIDEgMCAwMS40My41NGwuOTg0IDIuOTVhMSAxIDAgMDAuOTQ5LjY4M2g0LjU1OGExIDEgMCAwMC45NDktLjY4NGwuOTgyLTIuOTQ3YTEgMSAwIDAxLjQzNS0uNTQybC45ODItLjU4N2ExIDEgMCAwMS43OS0uMTAzbDIuNTkuNzQ1YTEgMSAwIDAwMS4xNDItLjQ2MWwyLjIyMi0zLjg0OGExIDEgMCAwMC0uMTY2LTEuMjE0bC0xLjkzMy0xLjg5NmExIDEgMCAwMS0uMy0uNzEzdi0xLjVhMSAxIDAgMDEuMy0uNzEzbDEuOTMzLTEuODk2YTEgMSAwIDAwLjE2Ni0xLjIxNGwtMi4yMjItMy44NDhhMSAxIDAgMDAtMS4xNDItLjQ2bC0yLjYuNzQ3YTEgMSAwIDAxLS43NzQtLjA5M2wtMS4zMS0uNzVhMSAxIDAgMDEtLjQ3NC0uNjI1bC0uNjYtMi42NHoiLz48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSI1Ii8+PC9zdmc+"
STATS_ICON_DARK_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2UwZTBlMCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxsaW5lIHgxPSIxOCIgeTE9IjIwIiB4Mj0iMTgiIHkyPSIxMCI+PC9saW5lPjxsaW5lIHgxPSIxMiIgeTE9IjIwIiB4Mj0iMTIiIHkyPSI0Ij48L2xpbmU+PGxpbmUgeDE9IjYiIHkxPSIyMCIgeDI9IjYiIHkyPSIxNCI+PC9saW5lPjwvc3ZnPg=="
STATS_ICON_LIGHT_B64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzVENDAzNyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxsaW5lIHgxPSIxOCIgeTE9IjIwIiB4Mj0iMTgiIHkyPSIxMCI+PC9saW5lPjxsaW5lIHgxPSIxMiIgeTE9IjIwIiB4Mj0iMTIiIHkyPSI0Ij48L2xpbmU+PGxpbmUgeDE9IjYiIHkxPSIyMCIgeDI9IjYiIHkyPSIxNCI+PC9saW5lPjwvc3ZnPg=="

# --- СТИЛИ (QSS) ---
DARK_STYLE = """
    QDialog { background-color: #2E2E2E; border: 1px solid #555; }
    QMainWindow, QWidget, QMenu { background-color: #2E2E2E; color: #E0E0E0; }
    QWidget { selection-background-color: #555555; selection-color: #FFFFFF; }
    QListWidget { background-color: #2E2E2E; border: 1px solid #4A4A4A; border-radius: 5px; }
    QListWidget::item { border-bottom: 1px solid #404040; padding: 5px; }
    QListWidget::item:selected { background-color: #555555; color: #E0E0E0; border-radius: 0px; }
    ResultItemWidget QLabel { background: transparent; }
    QFrame[frameShape="4"] { color: #4A4A4A; border: none; background-color: #4A4A4A; max-height: 1px; }

    QFrame#StatsCard { background-color: #3C3C3C; border: 1px solid #555; border-radius: 8px; }
    QLabel#StatsTitle { font-size: 11px; color: #AAAAAA; background: transparent; text-transform: uppercase; letter-spacing: 1px; }
    QLabel#StatsValue { font-size: 18px; font-weight: bold; color: #FFFFFF; background: transparent; }
    QLabel#StatsSub { font-size: 10px; color: #888888; background: transparent; }

    #UpdateBanner { background-color: #383838; }
    #UpdateBanner QLabel { color: #E0E0E0; font-weight: bold; font-size: 13px; }
    #UpdateBanner QPushButton { background-color: #505050; color: #FFF; border: 1px solid #606060; padding: 3px 10px; border-radius: 4px; font-size: 12px; }
    #UpdateBanner QPushButton:hover { background-color: #606060; }
    #UpdateBanner QPushButton#CloseBtn { background-color: transparent; border: none; color: #AAA; font-weight: bold; font-size: 16px; padding: 0px; }
    #UpdateBanner QPushButton#CloseBtn:hover { color: #FFF; background-color: transparent; }

    QLabel#loader_text { font-size: 18px; font-weight: bold; color: #E0E0E0; }
    QLabel#loader_quote { font-size: 14px; font-style: italic; color: #888888; }

    /* ВЕРТИКАЛЬНЫЙ СКРОЛЛБАР */
    QScrollBar:vertical { border: 1px solid #4A4A4A; background: #2E2E2E; width: 12px; margin: 0px; }
    QScrollBar::handle:vertical { background: #555; min-height: 20px; border-radius: 4px; margin: 1px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

    /* ГОРИЗОНТАЛЬНЫЙ СКРОЛЛБАР */
    QScrollBar:horizontal { border: 1px solid #4A4A4A; background: #2E2E2E; height: 12px; margin: 0px; }
    QScrollBar::handle:horizontal { background: #555; min-width: 20px; border-radius: 4px; margin: 1px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; border: none; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

    QSplitter::handle { background: transparent; border: none; }
    QLineEdit { background-color: #3C3C3C; border: 1px solid #555555; border-radius: 5px; padding: 5px; padding-left: 8px; color: #E0E0E0; font-size: 14px; }
    QPushButton { background-color: #555555; border: 1px solid #666666; padding: 5px 10px; border-radius: 5px; }
    QPushButton:hover { background-color: #666666; }
    QPushButton:disabled { background-color: #404040; color: #777; border: 1px solid #444; }
    QMenu::item:selected { background-color: #555555; }
    QCompleter QAbstractItemView { background-color: #3C3C3C; border: 1px solid #555555; color: #E0E0E0; }
    QCompleter QAbstractItemView::item:selected { background-color: #555555; }
    QLabel#placeholder_text { color: #888888; font-size: 16px; }
    QLabel#filename_label { color: #FFFFFF; font-weight: bold; font-size: 13px; background: transparent; }
    QLabel#path_label { color: #AAAAAA; font-size: 10px; background: transparent; }
    QLabel#fragments_count_label { color: #888888; font-size: 10px; font-style: italic; background: transparent; }

    QPlainTextEdit { background-color: #3C3C3C; border: 1px solid #4A4A4A; border-radius: 5px; padding: 8px; font-size: 13px; color: #E0E0E0; }
    QTextEdit { background-color: #3C3C3C; border: 1px solid #4A4A4A; border-radius: 5px; padding: 8px; font-size: 13px; color: #E0E0E0; }

    QStatusBar { background-color: #2E2E2E; color: #AAAAAA; border-top: 1px solid #444; }
    QStatusBar::item { border: none; } 
    QComboBox { background-color: #3C3C3C; border: 1px solid #555; border-radius: 3px; padding: 3px; color: #E0E0E0; }
    QComboBox::drop-down { border: none; }
    QCheckBox { spacing: 5px; color: #E0E0E0; }

    #themeButton, #settingsButton, #statsButton { border: none; background-color: transparent; border-radius: 16px; }
    #themeButton:hover, #settingsButton:hover, #statsButton:hover { background-color: #444; }
    QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 10px; padding-top: 15px; font-weight: bold; color: #AAAAAA; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
    QTabWidget::pane { border: 1px solid #4A4A4A; }
    QTabBar::tab { background: #404040; color: #AAA; padding: 8px 12px; border: 1px solid #555; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
    QTabBar::tab:selected { background: #555; color: #FFF; font-weight: bold; }
    QTabBar::tab:hover { background: #4A4A4A; }

    /* --- ТУМБЛЕР ПАНЕЛИ ПАПОК --- */
    QPushButton#TumblerBtn { border: none; background: transparent; color: #888888; font-size: 16px; font-weight: bold; border-radius: 4px; padding: 0px; }
    QPushButton#TumblerBtn:hover { background-color: #555555; color: #FFFFFF; }
    QPushButton#TumblerBtn:pressed { background-color: #444444; }
"""

LIGHT_STYLE = """
    QDialog { background-color: #FAF9F6; border: 1px solid #D7CCC8; }
    QMainWindow, QWidget, QMenu { background-color: #FAF9F6; color: #5D4037; }
    QWidget { selection-background-color: #D7CCC8; selection-color: #3E2723; }
    QListWidget { background-color: #FFFFFF; border: 1px solid #D7CCC8; border-radius: 5px; }
    QListWidget::item { border-bottom: 1px solid #EFEBE9; padding: 5px; color: #5D4037; }
    QListWidget::item:selected { background-color: #EFEBE9; color: #3E2723; border-radius: 0px; }
    ResultItemWidget QLabel { background: transparent; }
    QFrame[frameShape="4"] { color: #D7CCC8; border: none; background-color: #D7CCC8; max-height: 1px; }

    QFrame#StatsCard { background-color: #FFFFFF; border: 1px solid #D7CCC8; border-radius: 8px; }
    QLabel#StatsTitle { font-size: 11px; color: #8D6E63; background: transparent; text-transform: uppercase; letter-spacing: 1px; }
    QLabel#StatsValue { font-size: 18px; font-weight: bold; color: #3E2723; background: transparent; }
    QLabel#StatsSub { font-size: 10px; color: #A1887F; background: transparent; }

    #UpdateBanner { background-color: #F5F0EB; }
    #UpdateBanner QLabel { color: #5D4037; font-weight: bold; font-size: 13px; }
    #UpdateBanner QPushButton { background-color: #FFFFFF; color: #5D4037; border: 1px solid #D7CCC8; padding: 3px 10px; border-radius: 4px; font-size: 12px; }
    #UpdateBanner QPushButton:hover { background-color: #EFEBE9; }
    #UpdateBanner QPushButton#CloseBtn { background-color: transparent; border: none; color: #A1887F; font-weight: bold; font-size: 16px; padding: 0px; }
    #UpdateBanner QPushButton#CloseBtn:hover { color: #5D4037; background-color: transparent; }

    QLabel#loader_text { font-size: 18px; font-weight: bold; color: #3E2723; }
    QLabel#loader_quote { font-size: 14px; font-style: italic; color: #8D6E63; }

    /* ВЕРТИКАЛЬНЫЙ СКРОЛЛБАР */
    QScrollBar:vertical { border: 1px solid #D7CCC8; background: #FAF9F6; width: 12px; margin: 0px; }
    QScrollBar::handle:vertical { background: #D7CCC8; min-height: 20px; border-radius: 4px; margin: 1px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

    /* ГОРИЗОНТАЛЬНЫЙ СКРОЛЛБАР */
    QScrollBar:horizontal { border: 1px solid #D7CCC8; background: #FAF9F6; height: 12px; margin: 0px; }
    QScrollBar::handle:horizontal { background: #D7CCC8; min-width: 20px; border-radius: 4px; margin: 1px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; border: none; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

    QSplitter::handle { background: transparent; border: none; }
    QLineEdit { background-color: #FFFFFF; border: 1px solid #D7CCC8; border-radius: 5px; padding: 5px; padding-left: 8px; color: #4E342E; font-size: 14px; }
    QPushButton { background-color: #EFEBE9; border: 1px solid #D7CCC8; padding: 5px 10px; border-radius: 5px; color: #5D4037; }
    QPushButton:hover { background-color: #E0D8D6; }
    QPushButton:disabled { background-color: #F5F0EB; color: #BCAAA4; border: 1px solid #E0D8D6; }
    QMenu::item:selected { background-color: #EFEBE9; color: #3E2723; }
    QCompleter QAbstractItemView { background-color: #FFFFFF; border: 1px solid #D7CCC8; color: #5D4037; }
    QCompleter QAbstractItemView::item:selected { background-color: #EFEBE9; color: #3E2723; }
    QLabel#placeholder_text { color: #8D6E63; font-size: 16px; }
    QLabel#filename_label { color: #3E2723; font-weight: bold; font-size: 13px; background: transparent; }
    QLabel#path_label { color: #8D6E63; font-size: 10px; background: transparent; }
    QLabel#fragments_count_label { color: #A1887F; font-size: 10px; font-style: italic; background: transparent; }

    QPlainTextEdit { background-color: #FFFFFF; border: 1px solid #D7CCC8; border-radius: 5px; padding: 8px; font-size: 13px; color: #5D4037; }
    QTextEdit { background-color: #FFFFFF; border: 1px solid #D7CCC8; border-radius: 5px; padding: 8px; font-size: 13px; color: #5D4037; }

    QStatusBar { background-color: #FAF9F6; color: #8D6E63; border-top: 1px solid #D7CCC8; }
    QStatusBar::item { border: none; }
    QComboBox { background-color: #FFFFFF; border: 1px solid #D7CCC8; border-radius: 3px; padding: 3px; color: #5D4037; }
    QComboBox::drop-down { border: none; }
    QCheckBox { spacing: 5px; color: #5D4037; }

    #themeButton, #settingsButton, #statsButton { border: none; background-color: transparent; border-radius: 16px; }
    #themeButton:hover, #settingsButton:hover, #statsButton:hover { background-color: #EFEBE9; }
    QGroupBox { border: 1px solid #D7CCC8; border-radius: 5px; margin-top: 10px; padding-top: 15px; font-weight: bold; color: #8D6E63; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
    QTabWidget::pane { border: 1px solid #D7CCC8; }
    QTabBar::tab { background: #F5F0EB; color: #8D6E63; padding: 8px 12px; border: 1px solid #D7CCC8; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
    QTabBar::tab:selected { background: #EFEBE9; color: #3E2723; font-weight: bold; }
    QTabBar::tab:hover { background: #EFEBE9; }

    /* --- ТУМБЛЕР ПАНЕЛИ ПАПОК --- */
    QPushButton#TumblerBtn { border: none; background: transparent; color: #A1887F; font-size: 16px; font-weight: bold; border-radius: 4px; padding: 0px; }
    QPushButton#TumblerBtn:hover { background-color: #EFEBE9; color: #3E2723; }
    QPushButton#TumblerBtn:pressed { background-color: #D7CCC8; }
"""

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def format_filesize(size_in_bytes):
    if size_in_bytes is None: return "0 B"
    try:
        size_in_bytes = int(size_in_bytes)
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1024 ** 2:
            return f"{size_in_bytes / 1024:.1f} KB"
        elif size_in_bytes < 1024 ** 3:
            return f"{size_in_bytes / 1024 ** 2:.1f} MB"
        else:
            return f"{size_in_bytes / 1024 ** 3:.1f} GB"
    except (ValueError, TypeError):
        return "N/A"

def get_auto_tesseract_path():
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.getenv('LOCALAPPDATA', ''), r"Tesseract-OCR\tesseract.exe")
    ]
    for path in possible_paths:
        if os.path.exists(path): return path
    if shutil.which("tesseract"): return "tesseract"
    return ""

def fetch_tesseract_languages(tesseract_path):
    if not tesseract_path or not os.path.exists(tesseract_path):
        return ['eng', 'rus', 'rus+eng']
    try:
        result = subprocess.run([tesseract_path, '--list-langs'], capture_output=True, text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
        langs = [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith('List of')]
        if not langs: return ['eng', 'rus', 'rus+eng']
        if 'rus' in langs and 'eng' in langs: langs.insert(0, 'rus+eng')
        return langs
    except Exception:
        return ['eng', 'rus', 'rus+eng']

# --- МЕНЕДЖЕР КОНФИГУРАЦИИ (Поддержка умных папок) ---
class ConfigManager:
    def __init__(self, filename):
        self.filepath = filename

    def load_config(self):
        default_config = {
            "folders": [],
            "global_exts": ALL_SUPPORTED_EXTS.copy(),
            "history": [],
            "ocr_enabled": False,
            "tesseract_path": get_auto_tesseract_path(),
            "ocr_lang": "rus+eng",
            "font_size": 13,
            "max_file_size": 50,
            "ocr_dpi": 150,
            "is_dark_theme": True,
            "is_panel_visible": True,
            "auto_sync_enabled": False,
            "auto_sync_mode": "daily",
            "auto_sync_time": "14:00",
            "auto_sync_datetime": "",
            # --- НОВЫЕ КЛЮЧИ ДЛЯ НЕДЕЛЬНОГО РАСПИСАНИЯ ---
            "auto_sync_day": 0, # 0 - Понедельник, 6 - Воскресенье
            "auto_sync_weekly_time": "18:00"
        }
        if not os.path.exists(self.filepath):
            return default_config
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                config = default_config.copy()
                config.update(data)

                new_folders = []
                for folder in config["folders"]:
                    if isinstance(folder, str):
                        new_folders.append({"path": folder, "use_custom": False, "exts": []})
                    else:
                        new_folders.append(folder)
                config["folders"] = new_folders
                return config
        except (json.JSONDecodeError, IOError):
            return default_config

    def save_config(self, config_data):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            return True
        except IOError:
            return False

### БЛОК 3: Поисковый сервис (Whoosh & OCR)

# --- СЕРВИС ПОИСКА ---
class SearchService:
    def __init__(self, index_dir):
        self.index_dir = index_dir
        self.ocr_enabled = False
        self.tesseract_path = ""
        self.ocr_lang = "rus+eng"
        self.max_file_size_mb = 50
        self.ocr_dpi = 150
        self._word_app = None  # КЭШ ДЛЯ ФОНОВОГО WORD
        self.schema = Schema(
            path=ID(stored=True, unique=True),
            filename=TEXT(stored=True),
            filesize=NUMERIC(stored=True, sortable=True),
            mod_date=DATETIME(stored=True, sortable=True),
            file_ext=ID(stored=True),
            content=TEXT(analyzer=LanguageAnalyzer('ru'), stored=True)
        )

    def update_config(self, ocr_enabled, tesseract_path, ocr_lang, max_file_size, ocr_dpi):
        self.ocr_enabled = ocr_enabled
        self.tesseract_path = tesseract_path
        self.ocr_lang = ocr_lang
        self.max_file_size_mb = max_file_size
        self.ocr_dpi = ocr_dpi
        if self.ocr_enabled and OCR_AVAILABLE and self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    # --- МЕТОДЫ ОПТИМИЗАЦИИ (БАТЧИНГ) ---
    def start_batch(self):
        """Открывает Word один раз перед началом массовой индексации"""
        if WIN32_AVAILABLE and platform.system() == 'Windows':
            try:
                pythoncom.CoInitialize()  # Регистрация потока в Windows
                self._word_app = win32com.client.DispatchEx("Word.Application")
                self._word_app.Visible = False
                self._word_app.DisplayAlerts = False  # Глушим всплывающие окна
            except Exception:
                self._word_app = None

    def end_batch(self):
        """Закрывает Word после завершения всей индексации"""
        if self._word_app:
            try:
                self._word_app.Quit()
            except Exception:
                pass
            self._word_app = None
        if WIN32_AVAILABLE and platform.system() == 'Windows':
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def extract_text(self, filepath):
        try:
            if os.path.getsize(filepath) > self.max_file_size_mb * 1024 * 1024:
                return ""

            ext = filepath.lower()

            # --- DOCX ---
            if ext.endswith(".docx"):
                try:
                    doc = docx.Document(filepath)
                    return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                except Exception:
                    return ""

            # --- DOC (СТАРЫЙ WORD) — ТЕПЕРЬ ОЧЕНЬ БЫСТРЫЙ ---
            elif ext.endswith(".doc"):
                if WIN32_AVAILABLE and platform.system() == 'Windows':
                    own_word = False
                    word = self._word_app  # Берем из кэша

                    if not word:  # Если вдруг запустили без start_batch
                        try:
                            pythoncom.CoInitialize()
                            word = win32com.client.DispatchEx("Word.Application")
                            word.Visible = False
                            word.DisplayAlerts = False
                            own_word = True
                        except Exception:
                            return ""

                    try:
                        doc = word.Documents.Open(os.path.abspath(filepath), ReadOnly=True)
                        text = doc.Content.Text
                        doc.Close(False)

                        if own_word:
                            word.Quit()
                            pythoncom.CoUninitialize()
                        return text
                    except Exception:
                        if own_word and word is not None:
                            try:
                                word.Quit(); pythoncom.CoUninitialize()
                            except:
                                pass
                        return ""
                else:
                    return ""

            # --- TXT ---
            elif ext.endswith(".txt"):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except Exception:
                    return ""

            # --- PDF ---
            elif ext.endswith(".pdf"):
                text = ""
                if fitz and hasattr(fitz, 'open'):
                    try:
                        with fitz.open(filepath) as doc:
                            for page in doc:
                                page_text = page.get_text("text")
                                if not page_text.strip() and self.ocr_enabled and OCR_AVAILABLE:
                                    try:
                                        pix = page.get_pixmap(dpi=self.ocr_dpi)
                                        img_data = pix.tobytes("png")
                                        image = Image.open(io.BytesIO(img_data))
                                        page_text = pytesseract.image_to_string(image, lang=self.ocr_lang)
                                    except Exception:
                                        pass
                                text += page_text + "\n\n"
                    except Exception:
                        return ""
                return text

            # --- ИЗОБРАЖЕНИЯ ---
            elif ext.endswith((".png", ".jpg", ".jpeg", ".bmp")):
                if self.ocr_enabled and OCR_AVAILABLE:
                    try:
                        image = Image.open(filepath)

                        # Уменьшаем огромные картинки перед OCR
                        # Это спасет от зависаний на файлах по 7-10 МБ
                        max_size = (2000, 2000)
                        image.thumbnail(max_size, Image.Resampling.LANCZOS)

                        # Если файл обрабатывается дольше 3000 секунд - пропускаем
                        return pytesseract.image_to_string(image, lang=self.ocr_lang, timeout=3000)
                    except RuntimeError:  # Сработает, если вышел таймаут
                        print(f"Таймаут OCR для файла: {filepath}")
                        return ""
                    except Exception as e:
                        return ""
                return ""

        except Exception:
            return ""
        return ""

    def search(self, query_string, allowed_exts=None, is_fuzzy=False):
        try:
            ix = open_dir(self.index_dir)
            with ix.searcher() as searcher:
                if is_fuzzy:
                    terms = []
                    for word in query_string.split():
                        # Динамическая дистанция: короткие слова ищем точнее
                        dist = 1 if len(word) < 6 else 2
                        fuzzy_content = FuzzyTerm("content", word, maxdist=dist)
                        fuzzy_filename = FuzzyTerm("filename", word, maxdist=dist)
                        terms.append(Or([fuzzy_content, fuzzy_filename]))
                    query = Or(terms)
                else:
                    parser = MultifieldParser(["content", "filename"], self.schema)
                    parser.add_plugin(PhrasePlugin())
                    query = parser.parse(query_string)

                filter_query = None
                if allowed_exts:
                    filter_query = Or([Term("file_ext", ext) for ext in allowed_exts])

                results = searcher.search(query, filter=filter_query, limit=200)
                results.formatter = HtmlFormatter(tagname='span', classname='match', termclass='match')
                results.fragmenter = ContextFragmenter(maxchars=300, surround=50)

                final_results = []
                for hit in results:
                    full_text = hit.get("content", "")
                    highlighted_text = hit.highlights("content", text=full_text, top=10)
                    if highlighted_text:
                        fragments_html = [frag.strip() for frag in highlighted_text.split("...") if frag.strip()]
                        fragments_plain = [re.sub('<[^<]+?>', '', frag) for frag in fragments_html]
                        final_results.append({
                            "filename": hit['filename'], "path": hit['path'],
                            "filesize": hit['filesize'], "mod_date": hit['mod_date'],
                            "fragments_html": fragments_html, "fragments_plain": fragments_plain,
                            "full_text": full_text
                        })
                return final_results
        except EmptyIndexError:
            raise IndexNotFoundError("Индекс не найден. Пожалуйста, проиндексируйте папки.")
        except Exception as e:
            raise SearchServiceError(f"Произошла ошибка поиска: {e}")

    def get_statistics(self):
        stats = {
            "total_docs": 0,
            "total_size": 0,
            "types": {},
            "largest_file": {"name": "Нет данных", "size": 0},
            "newest_file": {"name": "Нет данных", "date": None},
            "avg_size": 0
        }
        try:
            ix = open_dir(self.index_dir)
            with ix.searcher() as searcher:
                latest_ts = 0
                max_size = 0

                for doc in searcher.all_stored_fields():
                    f_size = doc.get("filesize", 0)
                    f_date = doc.get("mod_date", None)
                    f_name = doc.get("filename", "Unknown")

                    stats["total_size"] += f_size
                    ext = doc.get("file_ext", "other")
                    stats["types"][ext] = stats["types"].get(ext, 0) + 1

                    if f_size > max_size:
                        max_size = f_size
                        stats["largest_file"] = {"name": f_name, "size": f_size}

                    if f_date:
                        ts = f_date.timestamp()
                        if ts > latest_ts:
                            latest_ts = ts
                            stats["newest_file"] = {"name": f_name, "date": f_date}

                # Реальное количество документов на основе посчитанных типов
                stats["total_docs"] = sum(stats["types"].values())

                if stats["total_docs"] > 0:
                    stats["avg_size"] = stats["total_size"] / stats["total_docs"]
        except Exception:
            pass
        return stats

# --- УМНЫЙ WATCHDOG ---
def get_allowed_exts_for_path(path, folders_config, global_exts):
    """ Проверяет, какие расширения разрешены для конкретного файла """
    path_norm = os.path.normpath(path)
    for f in folders_config:
        f_norm = os.path.normpath(f["path"])
        if path_norm.startswith(f_norm):
            if f.get("use_custom"):
                return f.get("exts", [])
            else:
                return global_exts
    return global_exts


# --- ПОТОК ИНДЕКСАЦИИ ---
class IndexingThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, search_service, folders_config, global_exts, mode='full', target_folder=None):
        super().__init__()
        self.search_service = search_service
        self.folders_config = folders_config
        self.global_exts = global_exts
        self.mode = mode  # 'full', 'sync' или 'folder'
        self.target_folder = target_folder

        # Списки для умной синхронизации
        self.files_to_index = []
        self.files_to_remove = []

    def is_file_allowed(self, filepath):
        allowed = get_allowed_exts_for_path(filepath, self.folders_config, self.global_exts)
        return any(filepath.lower().endswith(ext) for ext in allowed)

    def prepare_smart_sync(self):
        """ Сравнивает файлы на диске с базой Whoosh (Вычисляет Дельту) """
        ix = open_dir(self.search_service.index_dir)
        indexed_files = {}

        # 1. Читаем все даты из базы
        with ix.searcher() as searcher:
            for doc in searcher.all_stored_fields():
                dt = doc.get('mod_date')

                # СТАНДАРТИЗАЦИЯ ПУТИ ИЗ БАЗЫ
                path_key = os.path.normpath(doc['path'])
                if platform.system() == 'Windows':
                    path_key = path_key.lower()  # В Windows пути нечувствительны к регистру

                # Сохраняем оригинальный путь (чтобы корректно удалить) и время в ЦЕЛЫХ секундах
                indexed_files[path_key] = {
                    'original_path': doc['path'],
                    'mtime': int(dt.timestamp()) if dt else 0
                }

        # 2. Читаем все даты с диска
        current_files = {}
        for f_conf in self.folders_config:
            for root, _, files in os.walk(f_conf["path"]):
                for file in files:
                    if file.startswith('~$'): continue
                    filepath = os.path.normpath(os.path.join(root, file))
                    if self.is_file_allowed(filepath):
                        try:
                            # СТАНДАРТИЗАЦИЯ ПУТИ С ДИСКА
                            path_key = filepath
                            if platform.system() == 'Windows':
                                path_key = path_key.lower()

                            current_files[path_key] = {
                                'original_path': filepath,
                                'mtime': int(os.path.getmtime(filepath))  # Отбрасываем микросекунды!
                            }
                        except OSError:
                            pass

        # 3. Сравниваем стандартизированные списки
        for path_key, data in current_files.items():
            if path_key not in indexed_files:
                # Файла вообще нет в базе -> Добавляем
                self.files_to_index.append(data['original_path'])
            elif data['mtime'] > indexed_files[path_key]['mtime']:
                # Файл на диске новее (даже на 1 секунду) -> Обновляем
                self.files_to_index.append(data['original_path'])

        for path_key, data in indexed_files.items():
            if path_key not in current_files:
                # Файл есть в базе, но пропал с диска -> Удаляем
                self.files_to_remove.append(data['original_path'])

    def run(self):
        self.search_service.start_batch()
        try:
            # --- РЕЖИМ 1: УМНАЯ СИНХРОНИЗАЦИЯ ---
            if self.mode == 'sync':
                if not os.path.exists(self.search_service.index_dir):
                    self.mode = 'full'  # Если базы нет, делаем полную
                else:
                    self.progress.emit("Анализ изменений на диске...")
                    self.prepare_smart_sync()

                    if not self.files_to_index and not self.files_to_remove:
                        self.progress.emit("Все файлы актуальны!")
                        self.finished.emit(0)
                        return

                    ix = open_dir(self.search_service.index_dir)
                    writer = ix.writer(limitmb=512)
                    count = 0

                    for path in self.files_to_remove:
                        writer.delete_by_term('path', path)

                    total = len(self.files_to_index)
                    for i, filepath in enumerate(self.files_to_index):
                        if not os.path.exists(filepath): continue
                        percent = int(((i + 1) / total) * 100)
                        self.progress.emit(f"Синхронизация: {os.path.basename(filepath)} ({percent}%)")

                        text = self.search_service.extract_text(filepath)
                        try:
                            filesize = os.path.getsize(filepath)
                            mod_date = datetime.fromtimestamp(os.path.getmtime(filepath))
                            _, file_ext = os.path.splitext(filepath)
                            # update_document сам удалит старую копию и вставит новую
                            writer.update_document(path=filepath, filename=os.path.basename(filepath),
                                                   filesize=filesize, mod_date=mod_date,
                                                   file_ext=file_ext.lower(), content=text or "")
                            count += 1
                        except OSError:
                            pass

                    self.progress.emit("Сохранение изменений...")
                    writer.commit()
                    self.finished.emit(count)
                    return

            if self.mode == 'remove_folder' and self.target_folder:
                if not os.path.exists(self.search_service.index_dir):
                    self.finished.emit(0)
                    return

                self.progress.emit(f"Удаление данных папки из индекса...")
                ix = open_dir(self.search_service.index_dir)
                writer = ix.writer(limitmb=512)

                target_norm = os.path.normpath(self.target_folder)
                with ix.searcher() as searcher:
                    for doc in searcher.all_stored_fields():
                        # Если путь документа начинается с нашей папки - стираем его
                        if os.path.normpath(doc['path']).startswith(target_norm):
                            writer.delete_by_term('path', doc['path'])

                writer.commit()
                self.finished.emit(0)  # Передаем 0, так как мы ничего не проиндексировали
                return

            # --- РЕЖИМ 2: ОДНА ПАПКА ---
            if self.mode == 'folder' and self.target_folder:
                self.progress.emit(f"Очистка старых данных папки...")
                ix = open_dir(self.search_service.index_dir)
                writer = ix.writer(limitmb=512)

                target_norm = os.path.normpath(self.target_folder)
                with ix.searcher() as searcher:
                    for doc in searcher.all_stored_fields():
                        if os.path.normpath(doc['path']).startswith(target_norm):
                            writer.delete_by_term('path', doc['path'])

                files_to_add = []
                for root, _, files in os.walk(self.target_folder):
                    for file in files:
                        if file.startswith('~$'): continue
                        filepath = os.path.normpath(os.path.join(root, file))
                        if self.is_file_allowed(filepath):
                            files_to_add.append(filepath)

                total = len(files_to_add)
                count = 0
                for i, filepath in enumerate(files_to_add):
                    percent = int(((i + 1) / total) * 100) if total > 0 else 100
                    self.progress.emit(f"Индексация папки: {os.path.basename(filepath)} ({percent}%)")
                    text = self.search_service.extract_text(filepath)
                    try:
                        filesize = os.path.getsize(filepath)
                        mod_date = datetime.fromtimestamp(os.path.getmtime(filepath))
                        _, file_ext = os.path.splitext(filepath)
                        writer.add_document(path=filepath, filename=os.path.basename(filepath),
                                            filesize=filesize, mod_date=mod_date,
                                            file_ext=file_ext.lower(), content=text or "")
                        count += 1
                    except OSError:
                        pass

                self.progress.emit("Сохранение индекса папки...")
                writer.commit()
                self.finished.emit(count)
                return

            # --- РЕЖИМ 3: ПОЛНАЯ ПЕРЕИНДЕКСАЦИЯ ---
            self.progress.emit("Подсчет файлов...")
            files_to_add = []
            for f_conf in self.folders_config:
                folder_path = f_conf["path"]
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.startswith('~$'): continue
                        filepath = os.path.normpath(os.path.join(root, file))
                        if self.is_file_allowed(filepath):
                            files_to_add.append(filepath)

            total_files = len(files_to_add)
            if total_files == 0:
                self.finished.emit(0)
                return

            if os.path.exists(self.search_service.index_dir):
                shutil.rmtree(self.search_service.index_dir)
            os.makedirs(self.search_service.index_dir)

            ix = create_in(self.search_service.index_dir, self.search_service.schema)
            writer = ix.writer(limitmb=512)

            current_count = 0
            for i, filepath in enumerate(files_to_add):
                current_count += 1
                percent = int((current_count / total_files) * 100)
                self.progress.emit(f"Индексация: {os.path.basename(filepath)} ({percent}%)")
                text = self.search_service.extract_text(filepath)
                try:
                    filesize = os.path.getsize(filepath)
                    mod_date = datetime.fromtimestamp(os.path.getmtime(filepath))
                    _, file_ext = os.path.splitext(filepath)
                    writer.add_document(path=filepath, filename=os.path.basename(filepath), filesize=filesize,
                                        mod_date=mod_date, file_ext=file_ext.lower(), content=text or "")
                except OSError:
                    pass

            self.progress.emit("Сохранение индекса (это может занять время)...")
            writer.commit()
            self.finished.emit(current_count)

        except Exception as e:
            traceback.print_exc()
            self.progress.emit(f"Ошибка индексации: {e}")
            self.finished.emit(0)
        finally:
            self.search_service.end_batch()

# --- ПОТОК ПОИСКА ---
class SearchThread(QThread):
    finished = pyqtSignal(list, int)
    error = pyqtSignal(str)

    def __init__(self, search_service, query, allowed_exts, is_fuzzy):
        super().__init__()
        self.search_service = search_service
        self.query = query
        self.allowed_exts = allowed_exts
        self.is_fuzzy = is_fuzzy
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            results = self.search_service.search(self.query, self.allowed_exts, self.is_fuzzy)
            if not self._is_cancelled:
                self.finished.emit(results, len(results))
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(f"Внутренняя ошибка (см. консоль)")

def b64_to_icon(b64_string):
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(base64.b64decode(b64_string)), "SVG")
    return QIcon(pixmap)

# --- УМНЫЙ СПИСОК ПАПОК (С ПОДДЕРЖКОЙ ПЕРЕТАСКИВАНИЯ) ---
class DropListWidget(QListWidget):
    folder_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            folder_paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folder_paths.append(path)

            if folder_paths:
                self.folder_dropped.emit(folder_paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

# --- GUI ЭЛЕМЕНТЫ ---
class ResultItemWidget(QWidget):
    def __init__(self, filename, path, filesize_str, mod_date_str, fragments_count):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        filename_label = QLabel(filename)
        filename_label.setObjectName("filename_label")
        fragments_count_label = QLabel(f"(найдено {fragments_count} фрагментов)")
        fragments_count_label.setObjectName("fragments_count_label")
        top_layout.addWidget(filename_label)
        top_layout.addWidget(fragments_count_label)
        top_layout.addStretch()
        path_label = QLabel(f"{path} ({filesize_str})  |  Изменен: {mod_date_str}")
        path_label.setObjectName("path_label")
        layout.addLayout(top_layout)
        layout.addWidget(path_label)

class ChangesDialog(QDialog):
    def __init__(self, new_changed, deleted, is_dark, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Детали изменений")
        self.resize(600, 400)
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.list_new = QListWidget()
        for path in new_changed: self.list_new.addItem(path)
        self.tabs.addTab(self.list_new, f"Изменено/Добавлено ({len(new_changed)})")

        self.list_deleted = QListWidget()
        for path in deleted: self.list_deleted.addItem(path)
        self.tabs.addTab(self.list_deleted, f"Удалено ({len(deleted)})")

        layout.addWidget(self.tabs)
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

# --- ВИДЖЕТ ДИАГРАММЫ ---
class DonutChartWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setMinimumSize(220, 220)
        self.colors = [
            QColor("#81A1C1"), QColor("#BF616A"), QColor("#A3BE8C"),
            QColor("#EBCB8B"), QColor("#B48EAD"), QColor("#D08770"),
            QColor("#88C0D0"), QColor("#4C566A")
        ]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        center = rect.center()
        margin = 10
        outer_radius = min(rect.width(), rect.height()) // 2 - margin
        inner_radius = outer_radius * 0.65
        total = sum(self.data.values())
        if total == 0: return

        start_angle = 90 * 16
        sorted_data = sorted(self.data.items(), key=lambda x: x[1], reverse=True)

        for i, (label, value) in enumerate(sorted_data):
            color = self.colors[i % len(self.colors)]
            span_angle = -int((value / total) * 360 * 16)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(int(center.x() - outer_radius), int(center.y() - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2), start_angle, span_angle)
            start_angle += span_angle

        painter.setBrush(QBrush(self.parent().palette().window()))
        painter.drawEllipse(center, int(inner_radius), int(inner_radius))

# --- ДИАЛОГ СТАТИСТИКИ ---
class StatsDialog(QDialog):
    def __init__(self, stats_data, is_dark, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Аналитика базы знаний")
        self.resize(700, 450)
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        header = QLabel("Состояние поискового индекса")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(header)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        self.add_card(cards_layout, 0, 0, "Всего документов", str(stats_data['total_docs']), "")
        self.add_card(cards_layout, 0, 1, "Общий объем", format_filesize(stats_data['total_size']), "")
        self.add_card(cards_layout, 1, 0, "Самый большой файл", format_filesize(stats_data['largest_file']['size']),
                      stats_data['largest_file']['name'])

        date_str = "Нет данных"
        if stats_data['newest_file']['date']:
            date_str = stats_data['newest_file']['date'].strftime("%d.%m.%Y")
        self.add_card(cards_layout, 1, 1, "Самый свежий документ", date_str, stats_data['newest_file']['name'])
        layout.addLayout(cards_layout)

        h_split = QHBoxLayout()
        self.chart = DonutChartWidget(stats_data['types'], self)
        h_split.addWidget(self.chart, stretch=1)

        legend_layout = QVBoxLayout()
        legend_layout.setSpacing(8)
        sorted_types = sorted(stats_data['types'].items(), key=lambda x: x[1], reverse=True)
        total = stats_data['total_docs'] if stats_data['total_docs'] > 0 else 1

        for i, (ext, count) in enumerate(sorted_types):
            if i > 7: break
            color = self.chart.colors[i % len(self.chart.colors)].name()
            percent = int((count / total) * 100)
            if percent < 1: percent = "<1"

            row = QHBoxLayout()
            box = QLabel()
            box.setFixedSize(14, 14)
            box.setStyleSheet(f"background-color: {color}; border-radius: 4px;")

            lbl_name = QLabel(f"{ext}")
            lbl_name.setStyleSheet("font-weight: bold;")
            lbl_val = QLabel(f"{count} ({percent}%)")

            row.addWidget(box)
            row.addWidget(lbl_name)
            row.addStretch()
            row.addWidget(lbl_val)
            legend_layout.addLayout(row)

        legend_layout.addStretch()
        leg_widget = QWidget()
        leg_widget.setLayout(legend_layout)
        scroll = QScrollArea()
        scroll.setWidget(leg_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        h_split.addWidget(scroll, stretch=1)
        layout.addLayout(h_split)

        btn_close = QPushButton("Закрыть")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def add_card(self, layout, r, c, title, value, subtext):
        frame = QFrame()
        frame.setObjectName("StatsCard")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(15, 12, 15, 12)
        fl.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setObjectName("StatsTitle")
        v_lbl = QLabel(value)
        v_lbl.setObjectName("StatsValue")

        fl.addWidget(t_lbl)
        fl.addWidget(v_lbl)

        if subtext:
            s_lbl = QLabel(subtext)
            s_lbl.setObjectName("StatsSub")
            font_metrics = s_lbl.fontMetrics()
            elided = font_metrics.elidedText(subtext, Qt.TextElideMode.ElideMiddle, 200)
            s_lbl.setText(elided)
            s_lbl.setToolTip(subtext)
            fl.addWidget(s_lbl)

        layout.addWidget(frame, r, c)

# --- НАСТРОЙКИ ПАПКИ ---
class FolderSettingsDialog(QDialog):
    def __init__(self, folder_data, global_exts, is_dark, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки папки")
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Папка:\n{folder_data['path']}"))

        self.use_custom_cb = QCheckBox("Использовать индивидуальные типы файлов")
        self.use_custom_cb.setChecked(folder_data.get("use_custom", False))
        self.use_custom_cb.stateChanged.connect(self.toggle_exts)
        layout.addWidget(self.use_custom_cb)

        self.ext_group = QGroupBox("Индексируемые форматы")
        ext_layout = QGridLayout(self.ext_group)
        self.ext_cbs = {}

        row, col = 0, 0
        for ext in ALL_SUPPORTED_EXTS:
            cb = QCheckBox(ext)
            if folder_data.get("use_custom", False):
                cb.setChecked(ext in folder_data.get("exts", []))
            else:
                cb.setChecked(ext in global_exts)
                cb.setEnabled(False)
            self.ext_cbs[ext] = cb
            ext_layout.addWidget(cb, row, col)
            col += 1
            if col > 1: col = 0; row += 1

        layout.addWidget(self.ext_group)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def toggle_exts(self, state):
        is_custom = (state == 2)
        for cb in self.ext_cbs.values():
            cb.setEnabled(is_custom)

    def get_data(self):
        exts = [ext for ext, cb in self.ext_cbs.items() if cb.isChecked()]
        return {
            "use_custom": self.use_custom_cb.isChecked(),
            "exts": exts
        }


# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
class SettingsDialog(QDialog):
    def __init__(self, config, is_dark, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Глобальные настройки")
        self.resize(520, 680)  # Чуть увеличили окно
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)
        self.config = config

        layout = QVBoxLayout(self)

        ext_group = QGroupBox("Типы файлов по умолчанию")
        ext_layout = QGridLayout(ext_group)
        self.global_ext_cbs = {}
        row, col = 0, 0
        current_global = config.get("global_exts", ALL_SUPPORTED_EXTS)
        for ext in ALL_SUPPORTED_EXTS:
            cb = QCheckBox(ext)
            cb.setChecked(ext in current_global)
            self.global_ext_cbs[ext] = cb
            ext_layout.addWidget(cb, row, col)
            col += 1
            if col > 2: col = 0; row += 1
        layout.addWidget(ext_group)

        idx_group = QGroupBox("Индексация")
        idx_layout = QFormLayout(idx_group)
        self.max_size_edit = QLineEdit()
        self.max_size_edit.setValidator(QIntValidator(1, 10000))
        self.max_size_edit.setText(str(config.get("max_file_size", 50)))
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.max_size_edit)
        size_layout.addWidget(QLabel("МБ"))
        idx_layout.addRow("Макс. размер файла:", size_layout)
        layout.addWidget(idx_group)

        ocr_group = QGroupBox("Распознавание текста (OCR)")
        ocr_layout = QVBoxLayout(ocr_group)
        self.ocr_cb = QCheckBox("Включить OCR")
        self.ocr_cb.setChecked(config.get("ocr_enabled", False))

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(config.get("tesseract_path", ""))
        path_btn = QPushButton("...")
        path_btn.setFixedWidth(30)
        path_btn.clicked.connect(self.browse_tesseract)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Язык:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(fetch_tesseract_languages(self.path_edit.text()))
        current_lang = config.get("ocr_lang", "rus+eng")
        if current_lang in [self.lang_combo.itemText(i) for i in range(self.lang_combo.count())]:
            self.lang_combo.setCurrentText(current_lang)
        lang_layout.addWidget(self.lang_combo)

        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("Разрешение (DPI):"))
        self.dpi_edit = QLineEdit()
        self.dpi_edit.setValidator(QIntValidator(72, 1200))
        self.dpi_edit.setText(str(config.get("ocr_dpi", 150)))
        dpi_layout.addWidget(self.dpi_edit)

        ocr_layout.addWidget(self.ocr_cb)
        ocr_layout.addWidget(QLabel("Путь к Tesseract:"))
        ocr_layout.addLayout(path_layout)
        ocr_layout.addLayout(lang_layout)
        ocr_layout.addLayout(dpi_layout)
        layout.addWidget(ocr_group)

        # --- БЛОК ПЛАНИРОВЩИКА С НЕДЕЛЬНЫМ ГРАФИКОМ ---
        sync_group = QGroupBox("Автоматическое обновление базы")
        sync_layout = QVBoxLayout(sync_group)

        self.sync_cb = QCheckBox("Включить обновление по расписанию")
        self.sync_cb.setChecked(config.get("auto_sync_enabled", False))
        self.sync_cb.toggled.connect(self.toggle_sync_options)
        sync_layout.addWidget(self.sync_cb)

        self.sync_options_widget = QWidget()
        sync_opt_layout = QVBoxLayout(self.sync_options_widget)
        sync_opt_layout.setContentsMargins(20, 0, 0, 0)

        self.radio_group = QButtonGroup(self)
        self.radio_daily = QRadioButton("Каждый день в:")
        self.radio_weekly = QRadioButton("Каждую неделю:")  # <--- НОВАЯ КНОПКА
        self.radio_once = QRadioButton("Один раз (с календарем):")

        self.radio_group.addButton(self.radio_daily)
        self.radio_group.addButton(self.radio_weekly)
        self.radio_group.addButton(self.radio_once)

        # 1. Ежедневно
        daily_layout = QHBoxLayout()
        daily_layout.addWidget(self.radio_daily)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        default_time = QTime.fromString(config.get("auto_sync_time", "14:00"), "HH:mm")
        self.time_edit.setTime(default_time if default_time.isValid() else QTime(14, 0))
        daily_layout.addWidget(self.time_edit)
        daily_layout.addStretch()

        # 2. Еженедельно (НОВОЕ)
        weekly_layout = QHBoxLayout()
        weekly_layout.addWidget(self.radio_weekly)
        self.weekly_day_combo = QComboBox()
        self.weekly_day_combo.addItems(
            ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"])
        self.weekly_day_combo.setCurrentIndex(config.get("auto_sync_day", 0))

        self.weekly_time_edit = QTimeEdit()
        self.weekly_time_edit.setDisplayFormat("HH:mm")
        wt = QTime.fromString(config.get("auto_sync_weekly_time", "18:00"), "HH:mm")
        self.weekly_time_edit.setTime(wt if wt.isValid() else QTime(18, 0))

        weekly_layout.addWidget(self.weekly_day_combo)
        weekly_layout.addWidget(self.weekly_time_edit)
        weekly_layout.addStretch()

        # 3. Единожды
        once_layout = QHBoxLayout()
        once_layout.addWidget(self.radio_once)
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm")

        saved_dt_str = config.get("auto_sync_datetime", "")
        if saved_dt_str:
            try:
                dt = datetime.fromisoformat(saved_dt_str)
                self.datetime_edit.setDateTime(QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute))
            except ValueError:
                self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        else:
            self.datetime_edit.setDateTime(QDateTime.currentDateTime())

        once_layout.addWidget(self.datetime_edit)
        once_layout.addStretch()

        sync_opt_layout.addLayout(daily_layout)
        sync_opt_layout.addLayout(weekly_layout)
        sync_opt_layout.addLayout(once_layout)

        # Восстанавливаем выбранный режим
        mode = config.get("auto_sync_mode", "daily")
        if mode == "once":
            self.radio_once.setChecked(True)
        elif mode == "weekly":
            self.radio_weekly.setChecked(True)
        else:
            self.radio_daily.setChecked(True)

        sync_layout.addWidget(self.sync_options_widget)
        layout.addWidget(sync_group)
        self.toggle_sync_options(self.sync_cb.isChecked())

        maint_group = QGroupBox("Обслуживание")
        maint_layout = QHBoxLayout(maint_group)
        clear_btn = QPushButton("Очистить индекс поиска")
        clear_btn.clicked.connect(self.clear_index)
        maint_layout.addWidget(clear_btn)
        layout.addWidget(maint_group)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def toggle_sync_options(self, checked):
        self.sync_options_widget.setEnabled(checked)

    def browse_tesseract(self):
        file, _ = QFileDialog.getOpenFileName(self, "Укажите tesseract.exe", "", "Executable (*.exe);;All Files (*)")
        if file:
            self.path_edit.setText(file)
            self.lang_combo.clear()
            self.lang_combo.addItems(fetch_tesseract_languages(file))

    def clear_index(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Очистка")
        msg.setText("Весь поисковый индекс будет удален. Продолжить?")
        msg.setIcon(QMessageBox.Icon.Question)
        yes_btn = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            try:
                if os.path.exists(INDEX_DIR): shutil.rmtree(INDEX_DIR)
                QMessageBox.information(self, "Успех", "Индекс очищен.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить: {e}")

    def get_settings(self):
        try:
            font_s = int(self.font_size_edit.text())
        except ValueError:
            font_s = 13

        try:
            max_s = int(self.max_size_edit.text())
        except ValueError:
            max_s = 50

        try:
            dpi_s = int(self.dpi_edit.text())
        except ValueError:
            dpi_s = 150

        global_exts = [ext for ext, cb in self.global_ext_cbs.items() if cb.isChecked()]

        # Определяем режим
        if self.radio_once.isChecked():
            mode = "once"
        elif self.radio_weekly.isChecked():
            mode = "weekly"
        else:
            mode = "daily"

        qdt = self.datetime_edit.dateTime()
        dt_str = datetime(qdt.date().year(), qdt.date().month(), qdt.date().day(),
                          qdt.time().hour(), qdt.time().minute()).isoformat()

        return {
            "global_exts": global_exts,
            "ocr_enabled": self.ocr_cb.isChecked(),
            "tesseract_path": self.path_edit.text(),
            "ocr_lang": self.lang_combo.currentText(),
            "font_size": font_s,
            "max_file_size": max_s,
            "ocr_dpi": dpi_s,
            "auto_sync_enabled": self.sync_cb.isChecked(),
            "auto_sync_mode": mode,
            "auto_sync_time": self.time_edit.time().toString("HH:mm"),
            "auto_sync_datetime": dt_str,
            "auto_sync_day": self.weekly_day_combo.currentIndex(),
            "auto_sync_weekly_time": self.weekly_time_edit.time().toString("HH:mm")
        }

# --- ПРЕДПРОСМОТР ---
class PreviewWindow(QDialog):
    def __init__(self, filename, full_text, all_fragments, active_fragment_index, is_dark, font_size, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.filename = filename  # Сохраняем имя файла для заголовка
        self.total_fragments = len(all_fragments)
        self.active_fragment_index = active_fragment_index

        self.setGeometry(0, 0, 800, 600)

        self.full_text_content = full_text
        self.all_fragments = all_fragments
        self.is_dark_theme = is_dark
        self.font_size = font_size

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 15)
        layout.setSpacing(10)

        # ТЕКСТОВОЕ ПОЛЕ
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.text_edit.setPlainText(self.full_text_content)
        layout.addWidget(self.text_edit)

        # --- КРАСИВАЯ ПАНЕЛЬ НАВИГАЦИИ ВНИЗУ ---
        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.setSpacing(15)

        self.btn_prev = QPushButton("❮")
        self.btn_prev.setFixedSize(36, 32)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self.go_prev)

        self.lbl_info = QLabel()
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setMinimumWidth(80)  # Чтобы текст не "прыгал" при смене цифр

        self.btn_next = QPushButton("❯")
        self.btn_next.setFixedSize(36, 32)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self.go_next)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_info)
        nav_layout.addWidget(self.btn_next)

        layout.addLayout(nav_layout)

        self.update_theme(is_dark)
        self.update_nav_ui()

    def update_nav_ui(self):
        # Обновляем текст внизу и заголовок окна динамически
        current = self.active_fragment_index + 1
        self.lbl_info.setText(f"{current} из {self.total_fragments}")
        self.setWindowTitle(f"{self.filename} (Фрагмент {current} из {self.total_fragments})")

        self.btn_prev.setEnabled(self.active_fragment_index > 0)
        self.btn_next.setEnabled(self.active_fragment_index < self.total_fragments - 1)

    def go_prev(self):
        if self.active_fragment_index > 0:
            self.active_fragment_index -= 1
            self.update_nav_ui()
            self.highlight_all_fragments()

    def go_next(self):
        if self.active_fragment_index < self.total_fragments - 1:
            self.active_fragment_index += 1
            self.update_nav_ui()
            self.highlight_all_fragments()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(10, self.highlight_all_fragments)

    def update_font(self, size):
        self.font_size = size
        self.update_theme(self.is_dark_theme)

    def update_theme(self, is_dark):
        self.is_dark_theme = is_dark
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)

        bg_color = '#3C3C3C' if is_dark else '#FFFFFF'
        text_color = '#E0E0E0' if is_dark else '#5D4037'
        info_color = '#AAAAAA' if is_dark else '#8D6E63'

        btn_bg = '#555555' if is_dark else '#EFEBE9'
        btn_hover = '#666666' if is_dark else '#D7CCC8'
        btn_text = '#FFFFFF' if is_dark else '#3E2723'

        self.text_edit.setStyleSheet(
            f"font-size: {self.font_size}pt; border: none; background-color: {bg_color}; color: {text_color};")
        self.lbl_info.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {info_color}; background: transparent;")

        btn_style = f"""
            QPushButton {{ background-color: {btn_bg}; color: {btn_text}; border-radius: 6px; font-weight: bold; font-size: 16px; border: none; }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QPushButton:disabled {{ background-color: transparent; color: {'#555' if is_dark else '#D7CCC8'}; border: 1px solid {'#555' if is_dark else '#D7CCC8'}; }}
        """
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_next.setStyleSheet(btn_style)

        # ФИКС: Принудительно перерисовываем выделение текста, если окно открыто
        if hasattr(self, 'text_edit'):
            self.highlight_all_fragments()

    def find_fragment_cursor(self, fragment_text):
        search_text = re.escape(fragment_text.strip())
        search_pattern = re.sub(r'\\\s+', r'\\s+', search_text)

        match = re.search(search_pattern, self.full_text_content, re.DOTALL | re.IGNORECASE)
        if match:
            start_pos, end_pos = match.span()
            cursor = self.text_edit.textCursor()
            cursor.setPosition(start_pos)
            cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
            return cursor
        return None

    def highlight_all_fragments(self):
        extra_selections = []
        active_cursor = None

        bg_active = QColor("#D3D3D3") if self.is_dark_theme else QColor("#BCAAA4")
        fg_active = QColor("#000000") if self.is_dark_theme else QColor("#3E2723")

        bg_inactive = QColor("#666666") if self.is_dark_theme else QColor("#EFEBE9")
        fg_inactive = QColor("#FFFFFF") if self.is_dark_theme else QColor("#5D4037")

        for i, frag in enumerate(self.all_fragments):
            cursor = self.find_fragment_cursor(frag)
            if cursor:
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cursor

                if i == self.active_fragment_index:
                    sel.format.setBackground(bg_active)
                    sel.format.setForeground(fg_active)
                    active_cursor = cursor
                else:
                    sel.format.setBackground(bg_inactive)
                    sel.format.setForeground(fg_inactive)
                extra_selections.append(sel)

        self.text_edit.setExtraSelections(extra_selections)

        if active_cursor:
            self.text_edit.setTextCursor(active_cursor)
            self.text_edit.centerCursor()

# --- ГЛАВНОЕ ОКНО ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager(CONFIG_FILE)
        self.search_service = SearchService(INDEX_DIR)

        self.config = self.config_manager.load_config()
        self.folders_config = self.config["folders"]
        self.global_exts = self.config.get("global_exts", ALL_SUPPORTED_EXTS)
        self.search_history = deque(self.config["history"], maxlen=20)

        self.loading_quotes = [
            "Ищем иголку в стоге байтов...",
            "Опрашиваем жесткий диск с пристрастием...",
            "Разгоняем электроны вручную...",
            "Вспоминаем, куда вы положили этот файл...",
            "Завариваем кофе... (шутка, мы работаем)",
            "Подождите, гномы сортируют данные...",
            "Читаем мысли вашего компьютера...",
            "Проверяем под диваном...",
            "Почти нашли... наверное...",
            "Клянусь, этот файл был где-то здесь...",
            "Подождите, я только налью себе кофе...",
            "Просто наслаждайтесь моментом...",
            "Гадаем на кофейной гуще...",
            "Осталось опросить еще пару папок...",
            "Сколько еще я готов сделать ради этого документа?"
        ]

        self.apply_config_to_service()
        self.is_dark_theme = self.config.get("is_dark_theme", True)
        self.is_panel_visible = self.config.get("is_panel_visible", True)

        self.search_thread = None
        self.indexing_thread = None

        self.current_results = []
        self.preview_windows = []

        self.sun_icon = b64_to_icon(SUN_ICON_DARK_B64)
        self.moon_icon = b64_to_icon(MOON_ICON_LIGHT_B64)
        self.search_icon_dark = b64_to_icon(SEARCH_ICON_DARK_B64)
        self.search_icon_light = b64_to_icon(SEARCH_ICON_LIGHT_B64)
        self.settings_icon_dark = b64_to_icon(SETTINGS_ICON_DARK_B64)
        self.settings_icon_light = b64_to_icon(SETTINGS_ICON_LIGHT_B64)
        self.stats_icon_dark = b64_to_icon(STATS_ICON_DARK_B64)
        self.stats_icon_light = b64_to_icon(STATS_ICON_LIGHT_B64)

        self.setWindowTitle("Локальный поисковик")
        self.setGeometry(150, 150, 1100, 750)
        self.start_time = 0

        self.setup_ui()
        self.connect_signals()
        self.apply_theme()
        self.update_status_bar()
        self.set_buttons_enabled(True)

        if not self.is_panel_visible:
            self.hide_left_panel()

        self.loader_timer = QTimer()
        self.loader_timer.timeout.connect(self.update_loader)
        self.loader_chars = ['.', '..', '...']
        self.loader_idx = 0

        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self.update_status_spinner)
        self.spinner_chars = ['|', '/', '-', '\\']
        self.spinner_idx = 0
        self.current_status_text = ""

        # --- ТАЙМЕР ПЛАНИРОВЩИКА (Проверяет каждую минуту) ---
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self.check_schedule)
        self.scheduler_timer.start(60000)

    def apply_config_to_service(self):
        self.search_service.update_config(
            self.config.get("ocr_enabled", False),
            self.config.get("tesseract_path", ""),
            self.config.get("ocr_lang", "rus+eng"),
            self.config.get("max_file_size", 50),
            self.config.get("ocr_dpi", 150)
        )

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- ВЕРХНЯЯ ПАНЕЛЬ ---
        top_panel_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите запрос (Ctrl+F)...")
        self.completer = QCompleter(self)
        self.search_input.setCompleter(self.completer)
        self.update_completer()

        self.stats_button = QPushButton()
        self.stats_button.setObjectName("statsButton")
        self.stats_button.setFixedSize(36, 36)
        self.theme_switch_button = QPushButton()
        self.theme_switch_button.setObjectName("themeButton")
        self.theme_switch_button.setFixedSize(36, 36)
        self.settings_button = QPushButton()
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(36, 36)

        self.search_button_action = QAction(self)
        self.search_button_action.triggered.connect(self.perform_search)
        self.search_input.addAction(self.search_button_action, QLineEdit.ActionPosition.TrailingPosition)

        top_panel_layout.addWidget(self.search_input)
        top_panel_layout.addWidget(self.stats_button)
        top_panel_layout.addWidget(self.settings_button)
        top_panel_layout.addWidget(self.theme_switch_button)
        main_layout.addLayout(top_panel_layout)

        # --- ПАНЕЛЬ ФИЛЬТРОВ ---
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0, 5, 0, 5)
        options_layout.addWidget(QLabel("Искать в:"))
        self.pdf_filter_cb = QCheckBox(".pdf")
        self.pdf_filter_cb.setChecked(True)
        self.docx_filter_cb = QCheckBox(".docx")
        self.docx_filter_cb.setChecked(True)
        self.doc_filter_cb = QCheckBox(".doc")
        self.doc_filter_cb.setChecked(True)
        self.txt_filter_cb = QCheckBox(".txt")
        self.txt_filter_cb.setChecked(True)
        self.jpg_filter_cb = QCheckBox(".jpg/.png")
        self.jpg_filter_cb.setChecked(False)

        options_layout.addWidget(self.pdf_filter_cb)
        options_layout.addWidget(self.docx_filter_cb)
        options_layout.addWidget(self.doc_filter_cb)
        options_layout.addWidget(self.txt_filter_cb)
        options_layout.addWidget(self.jpg_filter_cb)
        options_layout.addStretch()
        self.fuzzy_cb = QCheckBox("Искать с учетом опечаток")
        options_layout.addWidget(self.fuzzy_cb)
        main_layout.addLayout(options_layout)

        # --- КНОПКА ВОЗВРАТА ПАНЕЛИ ---
        self.show_panel_btn = QPushButton("❯")
        self.show_panel_btn.setObjectName("TumblerBtn")
        self.show_panel_btn.setFixedSize(28, 28)
        self.show_panel_btn.setToolTip("Показать панель папок")
        self.show_panel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_panel_btn.hide()

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- ЛЕВАЯ ПАНЕЛЬ С ПАПКАМИ ---
        self.folder_panel = QWidget()
        folder_layout = QVBoxLayout(self.folder_panel)
        folder_layout.setContentsMargins(0, 0, 0, 0)

        folder_header_layout = QHBoxLayout()
        folder_label = QLabel("Папки для индексации:")

        self.toggle_panel_btn = QPushButton("❮")
        self.toggle_panel_btn.setObjectName("TumblerBtn")
        self.toggle_panel_btn.setFixedSize(28, 28)
        self.toggle_panel_btn.setToolTip("Скрыть панель папок")
        self.toggle_panel_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        folder_header_layout.addWidget(folder_label)
        folder_header_layout.addStretch()
        folder_header_layout.addWidget(self.toggle_panel_btn)

        self.folder_list_widget = DropListWidget()
        for f in self.folders_config:
            self.folder_list_widget.addItem(f["path"])

        self.folder_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_list_widget.customContextMenuRequested.connect(self.show_folder_context_menu)
        self.folder_list_widget.itemDoubleClicked.connect(self.open_folder_from_list)

        folder_buttons_layout = QHBoxLayout()
        self.add_folder_button = QPushButton("Добавить папку")
        folder_buttons_layout.addWidget(self.add_folder_button)

        self.sync_button = QPushButton("Актуализировать базу")

        self.reindex_button = QPushButton("Полная переиндексация")

        folder_layout.addLayout(folder_header_layout)
        folder_layout.addWidget(self.folder_list_widget)
        folder_layout.addLayout(folder_buttons_layout)
        folder_layout.addWidget(self.sync_button)
        folder_layout.addWidget(self.reindex_button)

        # --- ПРАВАЯ ПАНЕЛЬ С РЕЗУЛЬТАТАМИ ---
        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Сортировать по:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Релевантности", "Дате изменения (новые)", "Имени файла (А-Я)", "Размеру (большие)"])
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        results_layout.addLayout(sort_layout)

        self.results_stack = QStackedWidget()
        self.placeholder_widget = self.create_placeholder_widget()
        self.results_stack.addWidget(self.placeholder_widget)

        results_widget = QWidget()
        results_splitter_layout = QVBoxLayout(results_widget)
        results_splitter_layout.setContentsMargins(0, 0, 0, 0)
        results_splitter = QSplitter(Qt.Orientation.Vertical)

        self.results_list = QListWidget()
        self.snippet_view = QTextEdit()
        self.snippet_view.setObjectName("snippet_view")
        self.snippet_view.setReadOnly(True)
        self.snippet_view.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        results_splitter.addWidget(self.results_list)
        results_splitter.addWidget(self.snippet_view)
        results_splitter.setSizes([300, 400])
        results_splitter_layout.addWidget(results_splitter)
        self.results_stack.addWidget(results_widget)

        self.loading_widget = self.create_loading_widget()
        self.results_stack.addWidget(self.loading_widget)
        results_layout.addWidget(self.results_stack)

        main_splitter.addWidget(self.folder_panel)
        main_splitter.addWidget(results_panel)
        main_splitter.setSizes([300, 800])

        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)

        show_btn_layout = QVBoxLayout()
        show_btn_layout.addWidget(self.show_panel_btn)
        show_btn_layout.addStretch()

        middle_layout.addLayout(show_btn_layout)
        middle_layout.addWidget(main_splitter)
        main_layout.addLayout(middle_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)
        self.status_label = QLabel("")
        self.status_label.setContentsMargins(5, 0, 5, 0)
        self.status_bar.addWidget(self.status_label, 1)

    # --- ЛОГИКА ПЛАНИРОВЩИКА ---
    def check_schedule(self):
        if not self.config.get("auto_sync_enabled"): return
        if self.indexing_thread and self.indexing_thread.isRunning(): return

        mode = self.config.get("auto_sync_mode", "daily")
        now = datetime.now()
        current_hm = now.strftime("%H:%M")

        # Анти-дребезг: чтобы таймер не запустил процесс дважды за одну минуту
        if getattr(self, '_last_sync_time', None) == current_hm:
            return

        should_sync = False

        if mode == "daily":
            if current_hm == self.config.get("auto_sync_time", "14:00"):
                should_sync = True

        elif mode == "weekly":
            # now.weekday() возвращает: 0 - ПН, 1 - ВТ ... 6 - ВС
            target_day = self.config.get("auto_sync_day", 0)
            target_time = self.config.get("auto_sync_weekly_time", "18:00")
            if now.weekday() == target_day and current_hm == target_time:
                should_sync = True

        elif mode == "once":
            target_dt_str = self.config.get("auto_sync_datetime", "")
            if target_dt_str:
                try:
                    target_dt = datetime.fromisoformat(target_dt_str)
                    if now.date() == target_dt.date() and now.hour == target_dt.hour and now.minute == target_dt.minute:
                        should_sync = True
                        # Выключаем автообновление, т.к. оно было "на один раз"
                        self.config["auto_sync_enabled"] = False
                        self.save_current_config()
                except ValueError:
                    pass

        if should_sync:
            self._last_sync_time = current_hm
            self.start_smart_sync()

    def start_smart_sync(self):
        if not self.folders_config: return
        self.set_buttons_enabled(False)
        self.start_spinner()

        self.indexing_thread = IndexingThread(self.search_service, self.folders_config, self.global_exts, mode='sync')
        self.indexing_thread.progress.connect(self.set_status_message)
        self.indexing_thread.finished.connect(self.on_indexing_finished)
        self.indexing_thread.start()

    def set_status_message(self, text):
        self.current_status_text = text
        self.status_label.setText(text)

    def start_spinner(self):
        self.spinner_timer.start(100)

    def stop_spinner(self):
        self.spinner_timer.stop()
        self.status_label.setText(self.current_status_text)

    def update_status_spinner(self):
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
        char = self.spinner_chars[self.spinner_idx]
        self.status_label.setText(f"{self.current_status_text}  {char}")

    def create_placeholder_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label = QLabel(
            "Здесь появятся результаты поиска...\nВведите запрос в поле выше, чтобы начать (^.^)")
        placeholder_label.setObjectName("placeholder_text")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder_label)
        return widget

    def create_loading_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        self.loader_text_label = QLabel("Идет поиск...")
        self.loader_text_label.setObjectName("loader_text")
        self.loader_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loader_quote_label = QLabel("")
        self.loader_quote_label.setObjectName("loader_quote")
        self.loader_quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loader_text_label)
        layout.addWidget(self.loader_quote_label)
        return widget

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_F:
                self.search_input.setFocus()
                self.search_input.selectAll()
                return
        if event.key() == Qt.Key.Key_Escape:
            if self.search_input.hasFocus():
                self.search_input.clear()
            else:
                self.search_input.setFocus()
            return
        if event.key() == Qt.Key.Key_F5:
            self.start_full_indexing()
            return
        super().keyPressEvent(event)

    def connect_signals(self):
        self.search_input.returnPressed.connect(self.perform_search)
        self.theme_switch_button.clicked.connect(self.toggle_theme)
        self.settings_button.clicked.connect(self.open_settings)
        self.stats_button.clicked.connect(self.open_stats)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.reindex_button.clicked.connect(self.start_full_indexing)
        self.sync_button.clicked.connect(self.start_smart_sync)

        self.results_list.currentItemChanged.connect(self.display_snippets)
        self.results_list.itemDoubleClicked.connect(self.open_file_from_list)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_list_context_menu)
        self.snippet_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.snippet_view.customContextMenuRequested.connect(self.show_snippet_context_menu)
        self.sort_combo.currentIndexChanged.connect(self.sort_and_redisplay_results)
        self.toggle_panel_btn.clicked.connect(self.hide_left_panel)
        self.show_panel_btn.clicked.connect(self.show_left_panel)
        self.folder_list_widget.folder_dropped.connect(self.add_dropped_folders)

    def show_folder_context_menu(self, pos):
        item = self.folder_list_widget.itemAt(pos)
        if not item: return
        folder_path = item.text()

        menu = QMenu()
        open_action = QAction("Показать в Проводнике", self)
        copy_action = QAction("Копировать путь", self)
        settings_action = QAction("Настройки папки (Типы файлов)", self)
        reindex_action = QAction("Проиндексировать эту папку", self)
        remove_action = QAction("Удалить папку из базы", self)

        open_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path)))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(folder_path))
        settings_action.triggered.connect(lambda: self.open_folder_settings(folder_path))
        reindex_action.triggered.connect(lambda: self.start_single_folder_indexing(folder_path))
        remove_action.triggered.connect(lambda: self.remove_folder(item, folder_path))

        menu.addAction(open_action)
        menu.addAction(copy_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addAction(reindex_action)
        menu.addAction(remove_action)
        menu.exec(self.folder_list_widget.mapToGlobal(pos))

    def open_folder_settings(self, path):
        f_conf = next((f for f in self.folders_config if f["path"] == path), None)
        if not f_conf: return

        dlg = FolderSettingsDialog(f_conf, self.global_exts, self.is_dark_theme, self)
        if dlg.exec():
            data = dlg.get_data()
            f_conf.update(data)
            self.save_current_config()
            self.set_status_message(
                f"Настройки папки {os.path.basename(path)} сохранены. Рекомендуется переиндексация.")

    def start_single_folder_indexing(self, path):
        self.set_buttons_enabled(False)
        self.start_spinner()

        self.indexing_thread = IndexingThread(self.search_service, self.folders_config, self.global_exts,
                                              mode='folder', target_folder=path)
        self.indexing_thread.progress.connect(self.set_status_message)
        self.indexing_thread.finished.connect(self.on_indexing_finished)
        self.indexing_thread.start()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку", "", QFileDialog.Option.DontUseNativeDialog)
        if folder and not any(f["path"] == folder for f in self.folders_config):
            self.folders_config.append({"path": folder, "use_custom": False, "exts": []})
            self.folder_list_widget.addItem(folder)
            self.save_current_config()
            self.set_status_message("Папка добавлена. Выполните индексацию!")
        self.update_status_bar()

    def hide_left_panel(self):
        self.folder_panel.hide()
        self.show_panel_btn.show()

    def show_left_panel(self):
        self.show_panel_btn.hide()
        self.folder_panel.show()

    def add_dropped_folders(self, folder_paths):
        added_count = 0
        for folder in folder_paths:
            if not any(f["path"] == folder for f in self.folders_config):
                self.folders_config.append({"path": folder, "use_custom": False, "exts": []})
                self.folder_list_widget.addItem(folder)
                added_count += 1

        if added_count > 0:
            self.save_current_config()
            self.set_status_message(f"Добавлено папок: {added_count}. Рекомендуется полная переиндексация!")
            self.update_status_bar()

    def remove_folder(self, item, path):
        msg = QMessageBox(self)
        msg.setWindowTitle("Удаление папки")
        msg.setText(
            f"Удалить папку {os.path.basename(path)} из базы?\nВсе документы из этой папки будут стерты из индекса.")
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_yes = msg.addButton("Удалить", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Отмена", QMessageBox.ButtonRole.NoRole)
        msg.exec()

        if msg.clickedButton() == btn_yes:
            self.folders_config = [f for f in self.folders_config if f["path"] != path]
            self.folder_list_widget.takeItem(self.folder_list_widget.row(item))
            self.save_current_config()

            self.set_buttons_enabled(False)
            self.start_spinner()

            # ИСПРАВЛЕНИЕ: Вызываем с режимом 'remove_folder', а не 'folder'
            self.indexing_thread = IndexingThread(self.search_service, self.folders_config, self.global_exts,
                                                  mode='remove_folder', target_folder=path)
            self.indexing_thread.progress.connect(self.set_status_message)
            self.indexing_thread.finished.connect(self.on_indexing_finished)
            self.indexing_thread.start()

    def open_folder_from_list(self, item):
        path = item.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_stats(self):
        if not os.path.exists(INDEX_DIR):
            QMessageBox.warning(self, "Ошибка", "Индекс отсутствует. Сначала выполните индексацию.")
            return
        stats = self.search_service.get_statistics()
        dlg = StatsDialog(stats, self.is_dark_theme, self)
        dlg.exec()

    def start_full_indexing(self):
        if not self.folders_config: self.update_status_bar(); return
        self.set_buttons_enabled(False)
        self.start_spinner()
        self.indexing_thread = IndexingThread(self.search_service, self.folders_config, self.global_exts, mode='full')
        self.indexing_thread.progress.connect(self.set_status_message)
        self.indexing_thread.finished.connect(self.on_indexing_finished)
        self.indexing_thread.start()

    def on_indexing_finished(self, file_count):
        self.set_buttons_enabled(True)
        self.stop_spinner()
        self.set_status_message(f"Операция завершена! Обработано {file_count} файлов.")

    def perform_search(self):
        self.search_input.setEnabled(False)
        self.search_button_action.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        if not os.path.exists(INDEX_DIR) and self.folders_config:
            self.start_full_indexing()
            return
        self.query_text = self.search_input.text().strip()
        if not self.query_text:
            self.search_input.setEnabled(True)
            self.search_button_action.setEnabled(True)
            QApplication.restoreOverrideCursor()
            return

        self.add_to_history(self.query_text)
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.cancel()
            try:
                self.search_thread.finished.disconnect()
                self.search_thread.error.disconnect()
            except TypeError:
                pass

        self.results_list.clear()
        self.snippet_view.clear()
        self.current_results = []
        self.results_stack.setCurrentIndex(2)
        quote = random.choice(self.loading_quotes)
        self.loader_quote_label.setText(f"\"{quote}\"")
        self.loader_timer.start(250)
        self.start_spinner()
        self.set_status_message(f"Идет поиск \"{self.query_text}\"...")

        allowed_exts = []
        if self.pdf_filter_cb.isChecked(): allowed_exts.append(".pdf")
        if self.docx_filter_cb.isChecked(): allowed_exts.append(".docx")
        if self.doc_filter_cb.isChecked(): allowed_exts.append(".doc")
        if self.txt_filter_cb.isChecked(): allowed_exts.append(".txt")
        if self.jpg_filter_cb.isChecked(): allowed_exts.extend([".jpg", ".jpeg", ".png"])

        is_fuzzy = self.fuzzy_cb.isChecked()
        self.start_time = time.time()
        self.search_thread = SearchThread(self.search_service, self.query_text, allowed_exts, is_fuzzy)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()

    def update_loader(self):
        self.loader_idx = (self.loader_idx + 1) % len(self.loader_chars)
        dots = self.loader_chars[self.loader_idx]
        self.loader_text_label.setText(f"Идет поиск{dots}")

    def on_search_finished(self, results, total_count):
        self.search_input.setEnabled(True)
        self.search_input.setFocus()
        self.search_button_action.setEnabled(True)
        QApplication.restoreOverrideCursor()

        self.loader_timer.stop()
        self.stop_spinner()
        duration = time.time() - self.start_time
        self.current_results = results
        if total_count == 0:
            self.set_status_message("Ничего не найдено (´-ω-`)")
            self.results_stack.setCurrentIndex(0)
            return
        self.results_stack.setCurrentIndex(1)

        def pluralize_files(n):
            if n % 10 == 1 and n % 100 != 11:
                return f"{n} файл"
            elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
                return f"{n} файла"
            else:
                return f"{n} файлов"

        self.set_status_message(f"Найдено {pluralize_files(total_count)} за {duration:.2f} сек. ( ω ´ )و")
        self.sort_and_redisplay_results()

    def sort_and_redisplay_results(self):
        sort_key = self.sort_combo.currentText()
        sorted_results = self.current_results
        if sort_key == "Дате изменения (новые)":
            sorted_results = sorted(self.current_results, key=lambda r: r.get('mod_date'), reverse=True)
        elif sort_key == "Имени файла (А-Я)":
            sorted_results = sorted(self.current_results, key=lambda r: r.get('filename', '').lower())
        elif sort_key == "Размеру (большие)":
            sorted_results = sorted(self.current_results, key=lambda r: r.get('filesize', 0), reverse=True)

        self.results_list.clear()
        for i, hit_data in enumerate(sorted_results):
            item = QListWidgetItem(self.results_list)
            mod_date_str = hit_data.get('mod_date').strftime('%d.%m.%Y %H:%M') if hit_data.get('mod_date') else 'N/A'
            widget = ResultItemWidget(hit_data['filename'], hit_data['path'], format_filesize(hit_data['filesize']),
                                      mod_date_str, len(hit_data['fragments_html']))
            item.setSizeHint(widget.sizeHint())
            original_index = self.current_results.index(hit_data)
            item.setData(Qt.ItemDataRole.UserRole, original_index)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
        if self.results_list.count() > 0: self.results_list.setCurrentRow(0)

    def display_snippets(self, current_item, previous_item):
        if not current_item: self.snippet_view.clear(); return
        try:
            result_index = current_item.data(Qt.ItemDataRole.UserRole)
            hit_data = self.current_results[result_index]
            if hit_data['fragments_html']:
                base_text_color = "#5D4037" if not self.is_dark_theme else "#E0E0E0"
                font_size = self.config.get("font_size", 13)
                css = f"<style>body {{ font-family: sans-serif; font-size: {font_size}pt; color: {base_text_color}; }} .match {{ font-weight: bold; background-color: transparent; }} p {{ margin-bottom: 10px; }}</style>"
                fragments_joined = "".join([f"<p>...{frag}...</p>" for frag in hit_data['fragments_html']])
                self.snippet_view.setHtml(css + fragments_joined)
            else:
                self.snippet_view.setPlainText("Совпадений в тексте не найдено (поиск по имени файла).")
        except Exception:
            self.snippet_view.setPlainText(f"Не удалось отобразить фрагменты.")

    def show_snippet_context_menu(self, pos):
        cursor = self.snippet_view.cursorForPosition(pos)
        current_item = self.results_list.currentItem()
        if not current_item: return
        fragment_index = cursor.blockNumber()
        menu = QMenu()
        action = QAction("Открыть этот фрагмент в документе", self)
        action.triggered.connect(lambda: self.open_single_occurrence(current_item, fragment_index))
        menu.addAction(action)
        menu.exec(QCursor.pos())

    def open_single_occurrence(self, item, fragment_index):
        try:
            result_index = item.data(Qt.ItemDataRole.UserRole)
            hit_data = self.current_results[result_index]

            preview = PreviewWindow(
                filename=hit_data['filename'],
                full_text=hit_data['full_text'],
                all_fragments=hit_data['fragments_plain'],
                active_fragment_index=fragment_index,
                is_dark=self.is_dark_theme,
                font_size=self.config.get("font_size", 13),
                parent=self
            )

            new_list = []
            for w in self.preview_windows:
                try:
                    if w.isVisible():
                        new_list.append(w)
                except RuntimeError:
                    continue
            self.preview_windows = new_list
            self.preview_windows.append(preview)

            main_rect = self.geometry()
            preview_rect = preview.geometry()
            center_x = main_rect.x() + (main_rect.width() - preview_rect.width()) // 2
            center_y = main_rect.y() + (main_rect.height() - preview_rect.height()) // 2
            preview.move(center_x, center_y)

            preview.show()

        except Exception as e:
            traceback.print_exc()

    def on_search_error(self, error_message):
        self.search_input.setEnabled(True)
        self.search_input.setFocus()
        self.search_button_action.setEnabled(True)
        QApplication.restoreOverrideCursor()

        self.loader_timer.stop()
        self.stop_spinner()
        self.set_status_message(f"Ошибка: {error_message} (см. консоль)")

    def open_settings(self):
        dlg = SettingsDialog(self.config, self.is_dark_theme, self)
        if dlg.exec():
            new_settings = dlg.get_settings()
            self.config.update(new_settings)
            self.global_exts = new_settings["global_exts"]
            self.config_manager.save_config(self.config)
            self.apply_config_to_service()
            self.display_snippets(self.results_list.currentItem(), None)
            for window in self.preview_windows:
                if window.isVisible(): window.update_font(self.config["font_size"])

            self.set_status_message("Настройки сохранены!")

    def save_current_config(self):
        self.config["folders"] = self.folders_config
        self.config["global_exts"] = self.global_exts
        self.config["history"] = list(self.search_history)
        self.config["is_dark_theme"] = self.is_dark_theme
        self.config["is_panel_visible"] = self.folder_panel.isVisible()
        if not self.config_manager.save_config(self.config):
            self.set_status_message("Ошибка: не удалось сохранить конфигурацию.")

    def update_status_bar(self):
        current = self.status_label.text()
        if not current.startswith("Найдено") and not current.startswith("Индексация") and not current.startswith(
                "Фоновая") and not "поиск" in current:
            if not self.folders_config:
                self.set_status_message("Добавьте папки для индексации, чтобы начать (^.^)")
            elif not os.path.exists(INDEX_DIR):
                self.set_status_message("Требуется индексация ( ω ´ )و")
            else:
                self.set_status_message("Ожидание поискового запроса...")

    def set_buttons_enabled(self, enabled):
        for btn in [self.add_folder_button, self.search_input, self.reindex_button, self.sync_button]:
            btn.setEnabled(enabled)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

        for w in list(self.preview_windows):
            try:
                if w.isVisible():
                    w.update_theme(self.is_dark_theme)
            except RuntimeError:
                pass

        try:
            self.display_snippets(self.results_list.currentItem(), None)
        except Exception:
            pass

        self.save_current_config()

    def apply_theme(self):
        self.setStyleSheet(DARK_STYLE if self.is_dark_theme else LIGHT_STYLE)
        self.theme_switch_button.setIcon(self.sun_icon if self.is_dark_theme else self.moon_icon)
        self.theme_switch_button.setIconSize(QSize(24, 24))
        self.settings_button.setIcon(self.settings_icon_dark if self.is_dark_theme else self.settings_icon_light)
        self.settings_button.setIconSize(QSize(24, 24))
        self.stats_button.setIcon(self.stats_icon_dark if self.is_dark_theme else self.stats_icon_light)
        self.stats_button.setIconSize(QSize(24, 24))
        self.search_button_action.setIcon(self.search_icon_dark if self.is_dark_theme else self.search_icon_light)

    def update_completer(self):
        self.completer.setModel(QStringListModel(list(self.search_history)))

    def add_to_history(self, query):
        if query in self.search_history: self.search_history.remove(query)
        self.search_history.appendleft(query)
        self.save_current_config()
        self.update_completer()

    def get_path_from_list_item(self, item):
        if not item: return None
        try:
            result_index = item.data(Qt.ItemDataRole.UserRole)
            return self.current_results[result_index]['path']
        except (IndexError, TypeError):
            return None

    def copy_path_to_clipboard(self, path):
        QApplication.clipboard().setText(path)
        self.status_bar.showMessage("Путь к файлу скопирован в буфер обмена (^.^)", 3000)

    def open_file_from_list(self, item):
        file_path = self.get_path_from_list_item(item)
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        elif file_path:
            self.status_bar.showMessage("Ошибка: файл не найден по указанному пути.", 3000)

    def show_list_context_menu(self, pos):
        item = self.results_list.itemAt(pos)
        if not item: return
        file_path = self.get_path_from_list_item(item)
        if not file_path: return
        menu = QMenu()
        open_action = QAction("Открыть файл", self)
        open_folder_action = QAction("Показать в Проводнике", self)
        copy_path_action = QAction("Копировать путь к файлу", self)
        open_action.triggered.connect(lambda: self.open_file_from_list(item))
        if platform.system() == 'Windows':
            open_folder_action.triggered.connect(
                lambda: subprocess.run(['explorer', '/select,', os.path.normpath(file_path)], check=False))
        else:
            open_folder_action.triggered.connect(
                lambda: subprocess.run(['open', '-R', file_path]) if platform.system() == 'Darwin' else None)
        copy_path_action.triggered.connect(lambda: self.copy_path_to_clipboard(file_path))
        menu.addAction(open_action)
        menu.addAction(open_folder_action)
        menu.addAction(copy_path_action)
        menu.exec(self.results_list.mapToGlobal(pos))

    def closeEvent(self, event):
        if self.indexing_thread and self.indexing_thread.isRunning():
            msg = QMessageBox(self)
            msg.setWindowTitle("Прерывание работы")
            msg.setText(
                "Сейчас идет индексация файлов. Если вы закроете программу, база данных может сохраниться не полностью.\n\nВы уверены, что хотите выйти?")
            msg.setIcon(QMessageBox.Icon.Warning)
            btn_yes = msg.addButton("Да, выйти", QMessageBox.ButtonRole.YesRole)
            btn_no = msg.addButton("Отмена", QMessageBox.ButtonRole.NoRole)
            msg.exec()

            if msg.clickedButton() == btn_no:
                event.ignore()
                return

        for window in self.preview_windows:
            try:
                window.close()
            except RuntimeError:
                pass

        self.save_current_config()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())