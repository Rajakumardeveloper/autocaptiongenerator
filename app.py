import os
import json
import re
import shutil
import subprocess
import tempfile
import uuid
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from faster_whisper import WhisperModel

try:
    from indic_transliteration import sanscript
except ImportError:
    sanscript = None

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Small is a practical CPU default. You can set WHISPER_MODEL=medium or
# WHISPER_MODEL=large-v3 before starting the app when you want higher accuracy.
MODEL_SIZE = os.getenv("WHISPER_MODEL", "medium")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "500"))

app = FastAPI(title="AutoCaption AI")

model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE,
)

# Temporary editor sessions. Each session keeps the uploaded source video and
# transcription data until the user renders the final edited MP4.
EDITOR_SESSIONS = {}


# =========================================================
# CREATOR CAPTION TEMPLATES — CANONICAL DEFINITIONS
# =========================================================

CAPTION_TEMPLATES = {
    "bold_white": dict(
        font_name="Impact", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=4,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=0.62,
    ),
    "white_yellow": dict(
        font_name="Impact", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFE600",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=4,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=True,
        highlight_color="#FFE600", span_scale=0.62,
    ),
    "yellow_glow": dict(
        font_name="Impact", text_color="#FFE600", line1_color="#FFE600", line2_color="#FFE600",
        background_color="#000000", background_opacity=0, outline_color="#806C00", outline_width=2,
        shadow_distance=0, shadow_color="", glow=True, glow_color="#FFE600", glow_size=9,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "creator_bold": dict(
        font_name="Impact", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=6,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=64, border_style=1, highlight=True,
        highlight_color="#FFD400", span_scale=1.0,
    ),
    "clean_white": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#BBBBBB", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#111111", outline_width=1.5,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=False, italic=False, font_size=52, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=0.72,
    ),
    "yellow_bold": dict(
        font_name="Impact", text_color="#FFD800", line1_color="#FFD800", line2_color="#FFD800",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=5,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=60, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "black_box": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=90, outline_color="#000000", outline_width=0,
        shadow_distance=0, shadow_color="", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=52, border_style=3, highlight=True,
        highlight_color="#FFE600", span_scale=1.0,
    ),
    "white_box": dict(
        font_name="Arial", text_color="#111111", line1_color="#111111", line2_color="#111111",
        background_color="#FFFFFF", background_opacity=94, outline_color="#FFFFFF", outline_width=0,
        shadow_distance=0, shadow_color="", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=50, border_style=3, highlight=False,
        highlight_color="#111111", span_scale=1.0,
    ),
    "red_alert": dict(
        font_name="Impact", text_color="#FF3B30", line1_color="#FF3B30", line2_color="#FF3B30",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=4,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "cyan_pop": dict(
        font_name="Impact", text_color="#35E7FF", line1_color="#35E7FF", line2_color="#35E7FF",
        background_color="#000000", background_opacity=0, outline_color="#002B36", outline_width=4,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "blue_electric": dict(
        font_name="Arial", text_color="#4EA1FF", line1_color="#4EA1FF", line2_color="#4EA1FF",
        background_color="#000000", background_opacity=0, outline_color="#081B4A", outline_width=3.5,
        shadow_distance=4, shadow_color="#081B4A", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=56, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "pink_creator": dict(
        font_name="Impact", text_color="#FF5FD7", line1_color="#FF5FD7", line2_color="#FF5FD7",
        background_color="#000000", background_opacity=0, outline_color="#38002B", outline_width=4,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "soft_aesthetic": dict(
        font_name="Georgia", text_color="#F4F0EA", line1_color="#C8C0B5", line2_color="#F4F0EA",
        background_color="#303030", background_opacity=0, outline_color="#222222", outline_width=1,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=False, italic=True, font_size=48, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=0.72,
    ),
    "typewriter": dict(
        font_name="Courier New", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#141416", background_opacity=88, outline_color="#000000", outline_width=0,
        shadow_distance=0, shadow_color="", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=45, border_style=3, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "minimal_shadow": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=0,
        shadow_distance=6, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=54, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "news_ticker": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#D71920", background_opacity=95, outline_color="#D71920", outline_width=0,
        shadow_distance=0, shadow_color="", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=46, border_style=3, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "purple_neon": dict(
        font_name="Arial", text_color="#D58CFF", line1_color="#D58CFF", line2_color="#D58CFF",
        background_color="#000000", background_opacity=0, outline_color="#440066", outline_width=2,
        shadow_distance=0, shadow_color="", glow=True, glow_color="#C044FF", glow_size=9,
        bold=True, italic=False, font_size=56, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "green_focus": dict(
        font_name="Impact", text_color="#B8FF4A", line1_color="#B8FF4A", line2_color="#B8FF4A",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=4,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "cream_retro": dict(
        font_name="Georgia", text_color="#FFF0C2", line1_color="#FFF0C2", line2_color="#FFF0C2",
        background_color="#402B18", background_opacity=0, outline_color="#23170D", outline_width=2.5,
        shadow_distance=3, shadow_color="#23170D", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=50, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "editing_skool": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#FF8A00", background_opacity=95, outline_color="#8A3F00", outline_width=1,
        shadow_distance=2, shadow_color="#8A3F00", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=54, border_style=3, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "mr_beast": dict(
        font_name="Impact", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=6,
        shadow_distance=4, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=62, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "mr_beast_gold": dict(
        font_name="Impact", text_color="#FFD400", line1_color="#FFD400", line2_color="#FFD400",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=6,
        shadow_distance=4, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=62, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "highlight_orange": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=3,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=1, highlight=True,
        highlight_color="#FF9D00", span_scale=1.0,
    ),
    "green_glow": dict(
        font_name="Impact", text_color="#B8FF4A", line1_color="#B8FF4A", line2_color="#B8FF4A",
        background_color="#000000", background_opacity=0, outline_color="#184000", outline_width=2,
        shadow_distance=0, shadow_color="", glow=True, glow_color="#55FF00", glow_size=10,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "big_reveal": dict(
        font_name="Impact", text_color="#FFE600", line1_color="#FFE600", line2_color="#FFE600",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=6,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=70, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "deep_shadow": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=0,
        shadow_distance=8, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=56, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "aqua_pop": dict(
        font_name="Impact", text_color="#3DEBFF", line1_color="#3DEBFF", line2_color="#3DEBFF",
        background_color="#000000", background_opacity=0, outline_color="#003F52", outline_width=4,
        shadow_distance=3, shadow_color="#002230", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=60, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "red_black_punch": dict(
        font_name="Impact", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#D71920", background_opacity=95, outline_color="#000000", outline_width=4,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=58, border_style=3, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "clean_glow": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=0,
        shadow_distance=0, shadow_color="", glow=True, glow_color="#FFFFFF", glow_size=7,
        bold=False, italic=False, font_size=48, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "pixelated_word": dict(
        font_name="Courier New", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=2,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=50, border_style=1, highlight=True,
        highlight_color="#FFE600", span_scale=1.0,
    ),
    "liquid_glass": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#24285A", background_opacity=75, outline_color="#7D86FF", outline_width=1,
        shadow_distance=4, shadow_color="#4650C8", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=48, border_style=3, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "tabahi": dict(
        font_name="Georgia", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=2,
        shadow_distance=4, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=True, font_size=52, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "deep_glow": dict(
        font_name="Impact", text_color="#FF24FF", line1_color="#FF24FF", line2_color="#FF24FF",
        background_color="#000000", background_opacity=0, outline_color="#500050", outline_width=2,
        shadow_distance=0, shadow_color="", glow=True, glow_color="#FF24FF", glow_size=11,
        bold=True, italic=False, font_size=58, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=1.0,
    ),
    "highlighted_word": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFAE00",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=2,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=54, border_style=1, highlight=True,
        highlight_color="#FFAE00", span_scale=1.0,
    ),
    "delhi_editor": dict(
        font_name="Georgia", text_color="#FFFFFF", line1_color="#EEEEEE", line2_color="#FFFFFF",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=1,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=False, italic=True, font_size=52, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=0.88,
    ),
    "aura_blue": dict(
        font_name="Georgia", text_color="#8FE7FF", line1_color="#FFFFFF", line2_color="#8FE7FF",
        background_color="#000000", background_opacity=0, outline_color="#004E67", outline_width=2,
        shadow_distance=0, shadow_color="", glow=True, glow_color="#0088B0", glow_size=7,
        bold=True, italic=True, font_size=55, border_style=1, highlight=False,
        highlight_color="#FFFFFF", span_scale=0.88,
    ),
    "swiss_focus": dict(
        font_name="Arial", text_color="#FFFFFF", line1_color="#FFFFFF", line2_color="#FFD400",
        background_color="#000000", background_opacity=0, outline_color="#000000", outline_width=2,
        shadow_distance=2, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=False, font_size=60, border_style=1, highlight=True,
        highlight_color="#FFD400", span_scale=1.0,
    ),
    "scribble": dict(
        font_name="Georgia", text_color="#FFF4A3", line1_color="#FFF4A3", line2_color="#FFCF2E",
        background_color="#000000", background_opacity=0, outline_color="#222200", outline_width=1.5,
        shadow_distance=3, shadow_color="#000000", glow=False, glow_color="", glow_size=0,
        bold=True, italic=True, font_size=50, border_style=1, highlight=True,
        highlight_color="#FFCF2E", span_scale=0.88,
    ),
}


# =========================================================
# SINGLE SOURCE OF TRUTH FOR TEMPLATE FIDELITY
# =========================================================
TEMPLATE_META = {
    "bold_white": {"category":"Built-in Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":26, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "white_yellow": {"category":"Dynamic Captions", "chunk_words":3, "words_per_line":[2, 1], "max_chars":24, "max_lines":2, "text_case":"upper", "line_height":0.86, "letter_spacing":0, "position":"lower", "animation":"pop", "highlight_mode":"word"},
    "yellow_glow": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[2], "max_chars":24, "max_lines":1, "text_case":"upper", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"glow_pulse"},
    "creator_bold": {"category":"Built-in Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.82, "letter_spacing":0, "position":"center", "animation":"pop", "highlight_mode":"word"},
    "clean_white": {"category":"Static Captions", "chunk_words":4, "words_per_line":[2, 2], "max_chars":30, "max_lines":2, "text_case":"sentence", "line_height":0.92, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "yellow_bold": {"category":"Built-in Templates", "chunk_words":2, "words_per_line":[2], "max_chars":24, "max_lines":1, "text_case":"upper", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "black_box": {"category":"Static Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":25, "max_lines":2, "text_case":"upper", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"scale_in", "highlight_mode":"word"},
    "white_box": {"category":"Static Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":25, "max_lines":2, "text_case":"upper", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"scale_in"},
    "red_alert": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.86, "letter_spacing":0, "position":"center", "animation":"bounce"},
    "cyan_pop": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "blue_electric": {"category":"AI / Creator Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":25, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "pink_creator": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":23, "max_lines":2, "text_case":"upper", "line_height":0.86, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "soft_aesthetic": {"category":"Static Captions", "chunk_words":3, "words_per_line":[2, 1], "max_chars":30, "max_lines":2, "text_case":"sentence", "line_height":0.92, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "typewriter": {"category":"Static Captions", "chunk_words":3, "words_per_line":[2, 1], "max_chars":29, "max_lines":2, "text_case":"sentence", "line_height":0.90, "letter_spacing":0.5, "position":"lower", "animation":"scale_in"},
    "cream_retro": {"category":"Built-in Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":27, "max_lines":2, "text_case":"upper", "line_height":0.9, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "minimal_shadow": {"category":"Static Captions", "chunk_words":3, "words_per_line":[2, 1], "max_chars":31, "max_lines":2, "text_case":"sentence", "line_height":0.92, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "news_ticker": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":31, "max_lines":2, "text_case":"upper", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"slide"},
    "purple_neon": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":23, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"glow_pulse"},
    "green_focus": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":23, "max_lines":2, "text_case":"upper", "line_height":0.86, "letter_spacing":0, "position":"center", "animation":"pop"},
    "editing_skool": {"category":"AI / Creator Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "mr_beast": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"bounce"},
    "mr_beast_gold": {"category":"AI / Creator Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"bounce"},
    "highlight_orange": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":27, "max_lines":2, "text_case":"sentence", "line_height":0.90, "letter_spacing":0, "position":"lower", "animation":"pop", "highlight_mode":"word"},
    "green_glow": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":23, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"glow_pulse"},
    "big_reveal": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":18, "max_lines":2, "text_case":"upper", "line_height":0.82, "letter_spacing":0, "position":"center", "animation":"pop"},
    "deep_shadow": {"category":"Static Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":28, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "aqua_pop": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "red_black_punch": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"pop"},
    "clean_glow": {"category":"Built-in Templates", "chunk_words":4, "words_per_line":[2, 2], "max_chars":30, "max_lines":2, "text_case":"sentence", "line_height":0.92, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "pixelated_word": {"category":"Static Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"pop", "highlight_mode":"word"},
    "liquid_glass": {"category":"AI / Creator Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":26, "max_lines":2, "text_case":"sentence", "line_height":0.9, "letter_spacing":0, "position":"lower", "animation":"scale_in"},
    "tabahi": {"category":"AI / Creator Templates", "chunk_words":4, "words_per_line":[2, 2], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.84, "letter_spacing":0, "position":"center", "animation":"pop"},
    "deep_glow": {"category":"Dynamic Captions", "chunk_words":4, "words_per_line":[2, 2], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.88, "letter_spacing":0, "position":"lower", "animation":"glow_pulse"},
    "highlighted_word": {"category":"Dynamic Captions", "chunk_words":3, "words_per_line":[1, 2], "max_chars":26, "max_lines":2, "text_case":"sentence", "line_height":0.9, "letter_spacing":0, "position":"lower", "animation":"pop", "highlight_mode":"word"},
    "delhi_editor": {"category":"AI / Creator Templates", "chunk_words":4, "words_per_line":[2, 2], "max_chars":28, "max_lines":2, "text_case":"sentence", "line_height":0.92, "letter_spacing":0, "position":"lower", "animation":"fade"},
    "aura_blue": {"category":"AI / Creator Templates", "chunk_words":2, "words_per_line":[1, 1], "max_chars":22, "max_lines":2, "text_case":"upper", "line_height":0.86, "letter_spacing":0, "position":"center", "animation":"glow_pulse"},
    "swiss_focus": {"category":"Dynamic Captions", "chunk_words":2, "words_per_line":[1, 1], "max_chars":23, "max_lines":2, "text_case":"lower", "line_height":0.9, "letter_spacing":0, "position":"lower", "animation":"pop", "highlight_mode":"word"},
    "scribble": {"category":"AI / Creator Templates", "chunk_words":3, "words_per_line":[2, 1], "max_chars":23, "max_lines":2, "text_case":"sentence", "line_height":0.9, "letter_spacing":0, "position":"lower", "animation":"pop", "highlight_mode":"word"},
}

TEMPLATE_PRESENTATION = {
    "bold_white": ("Bold White", "Oversized", "t-bold-white", "MAKE IT", "BOLD"),
    "white_yellow": ("White + Yellow", "Creator", "t-white-yellow", "THIS IS", "IMPORTANT"),
    "yellow_glow": ("Yellow Glow", "Glow", "t-yellow-glow", "CAPTIONS", ""),
    "creator_bold": ("Creator Bold", "Big text", "t-creator-bold", "UNIQUE", "BOLD"),
    "clean_white": ("Clean White", "Minimal", "t-clean", "simple", "captions"),
    "yellow_bold": ("Yellow Bold", "High contrast", "t-yellow-bold", "INSTAGRAM", ""),
    "black_box": ("Black Box", "Readable", "t-black-box", "READABLE", "ANYWHERE"),
    "white_box": ("White Box", "Modern", "t-white-box", "CLEAN", "CARD"),
    "red_alert": ("Red Alert", "Punchy", "t-red-alert", "STOP", "SCROLLING"),
    "cyan_pop": ("Cyan Pop", "Neon", "t-cyan", "WATCH", "THIS"),
    "blue_electric": ("Blue Electric", "Tech", "t-blue", "LEVEL UP", "NOW"),
    "pink_creator": ("Pink Creator", "Social", "t-pink", "MAKE", "CONTENT"),
    "soft_aesthetic": ("Soft Aesthetic", "Vlog", "t-aesthetic", "a little", "different"),
    "typewriter": ("Typewriter", "Story", "t-typewriter", "TELL THE", "STORY"),
    "cream_retro": ("Cream Retro", "Retro", "t-cream-retro", "A LITTLE", "RETRO"),
    "minimal_shadow": ("Minimal Shadow", "Clean", "t-minimal", "SAY IT", "CLEARLY"),
    "news_ticker": ("News Ticker", "Breaking News", "t-news", "BREAKING", "NEWS"),
    "purple_neon": ("Purple Neon", "Neon", "t-purple", "CREATE", "MORE"),
    "green_focus": ("Green Focus", "Energy", "t-green", "FOCUS", "HERE"),
    "editing_skool": ("Editing Skool", "Creator", "t-editing-skool", "MAKE IT", "POP"),
    "mr_beast": ("Mr Beast Style", "Punchy", "t-mr-beast", "THE", "MOMENT"),
    "mr_beast_gold": ("Mr Beast Gold", "Gold", "t-mr-beast-gold", "THIS IS", "BIG"),
    "highlight_orange": ("Highlighted Word", "Dynamic", "t-highlight-orange", "WATCH", "THIS"),
    "green_glow": ("Creator Glow", "Glow", "t-green-glow", "GO", "VIRAL"),
    "big_reveal": ("Big Reveal", "Kinetic", "t-big-reveal", "THIS", "CHANGES"),
    "deep_shadow": ("Deep Shadow", "3D Shadow", "t-deep-shadow", "THE", "ANSWER"),
    "aqua_pop": ("Aqua Pop", "Neon", "t-aqua-pop", "LEVEL", "UP"),
    "red_black_punch": ("Red Punch", "Punchy", "t-red-black-punch", "STOP", "NOW"),
    "clean_glow": ("Clean Glow", "Ethereal", "t-clean-glow", "the quick", "brown fox"),
    "pixelated_word": ("Pixelated Word", "Retro", "t-pixelated", "THE", "BROWN"),
    "liquid_glass": ("Liquid Glass", "Glass", "t-liquid-glass", "the quick", "fox"),
    "tabahi": ("Tabahi", "Editorial", "t-tabahi", "THE QUICK", "BROWN FOX"),
    "deep_glow": ("Deep Glow", "Glow", "t-deep-glow", "BROWN FOX", "JUMPS OVER"),
    "highlighted_word": ("Highlighted Word", "Dynamic", "t-highlighted-word", "the", "quick fox"),
    "delhi_editor": ("Delhi", "Editorial", "t-delhi", "the quick", "brown fox"),
    "aura_blue": ("Aura", "Editorial", "t-aura-blue", "forget", "STATUS"),
    "swiss_focus": ("Swiss", "Editorial", "t-swiss", "focus", "DEEPLY"),
    "scribble": ("Scribble", "Handwritten", "t-scribble", "the little", "things"),
}


def get_template_object(template_id: str) -> dict:
    """Return the complete canonical template contract used everywhere."""
    if template_id not in CAPTION_TEMPLATES:
        template_id = "bold_white"
    base = dict(CAPTION_TEMPLATES[template_id])
    meta = dict(TEMPLATE_META.get(template_id, {}))
    name, tag, css_class, preview_a, preview_b = TEMPLATE_PRESENTATION.get(
        template_id, (template_id, "Creator", "t-bold-white", "CAPTION", "STYLE")
    )
    max_lines = int(meta.get("max_lines", 2))
    chunk_words = int(meta.get("chunk_words", 4))
    words_per_line = list(meta.get("words_per_line") or ([2, 1] if max_lines > 1 else [chunk_words]))
    base.update({
        "id": template_id,
        "name": name,
        "tag": tag,
        "category": meta.get("category", "Built-in Templates"),
        "css_class": css_class,
        "preview_a": preview_a,
        "preview_b": preview_b,
        "chunk_words": chunk_words,
        "words_per_line": words_per_line,
        "max_chars": int(meta.get("max_chars", 28)),
        "max_lines": max_lines,
        "text_case": meta.get("text_case", "sentence"),
        "line_height": float(meta.get("line_height", 0.90)),
        "letter_spacing": float(meta.get("letter_spacing", 0)),
        "position": meta.get("position", "lower"),
        "animation": meta.get("animation", "pop"),
        "highlight_mode": meta.get("highlight_mode", "none" if not base.get("highlight") else "word"),
        "padding_x": float(base.get("padding_x", 10)),
        "padding_y": float(base.get("padding_y", 4)),
        "border_radius": float(base.get("border_radius", 6)),
        "safe_area": 0.92,
        "version": 14,
    })
    return base


def all_template_objects() -> list[dict]:
    return [get_template_object(template_id) for template_id in CAPTION_TEMPLATES]


# Indic scripts that must never reach the caption UI/export in Hinglish mode.
INDIC_SCRIPT_RANGES = (
    ("devanagari", re.compile(r"[\u0900-\u097F]")),
    ("telugu", re.compile(r"[\u0C00-\u0C7F]")),
    ("bengali", re.compile(r"[\u0980-\u09FF]")),
    ("gujarati", re.compile(r"[\u0A80-\u0AFF]")),
    ("gurmukhi", re.compile(r"[\u0A00-\u0A7F]")),
    ("kannada", re.compile(r"[\u0C80-\u0CFF]")),
    ("malayalam", re.compile(r"[\u0D00-\u0D7F]")),
    ("tamil", re.compile(r"[\u0B80-\u0BFF]")),
)


def _indic_script(text: str):
    value = text or ""
    for name, pattern in INDIC_SCRIPT_RANGES:
        if pattern.search(value):
            return name
    return None


def romanize_hindi_word(text: str) -> str:
    """Return Latin-alphabet creator text. English stays English; Hindi is Romanized.

    Hinglish mode pins Whisper to Hindi so Hindi speech is not misclassified as
    Telugu. This final pass also prevents any accidental Indic-script leak from
    reaching the editor/export.
    """
    if not text:
        return text
    script = _indic_script(text)
    if not script or sanscript is None:
        return text
    source_map = {
        "devanagari": "DEVANAGARI",
        "telugu": "TELUGU",
        "bengali": "BENGALI",
        "gujarati": "GUJARATI",
        "gurmukhi": "GURMUKHI",
        "kannada": "KANNADA",
        "malayalam": "MALAYALAM",
        "tamil": "TAMIL",
    }
    try:
        source = getattr(sanscript, source_map[script])
        roman = sanscript.transliterate(text, source, sanscript.ITRANS).lower()
        roman = (
            roman.replace("~n", "n")
            .replace("~m", "m")
            .replace(".n", "n")
            .replace(".m", "m")
        )
        roman = re.sub(r"[^a-z0-9' -]", "", roman)
        roman = re.sub(r"\s+", " ", roman).strip()
        if script == "devanagari":
            casual = {
                "kaise": "kese", "kaisa": "kesa", "kaisi": "kesi",
                "aise": "ese", "waise": "wese", "jaise": "jese",
                "kyun": "kyu", "nahi": "nahi", "nahin": "nahi",
                "hain": "hai", "hoon": "hu", "hu": "hu",
            }
            roman = casual.get(roman, roman)
        return roman or text
    except Exception:
        # Never crash caption generation because of a transliteration edge case.
        return text


def clean_creator_word(text: str) -> str:
    """Normalize spacing/punctuation without changing the spoken language."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text


def maybe_romanize_words(words, mode: str):
    """Romanize Hindi script in Hinglish/auto modes while preserving English words."""
    converted = []
    for word in words:
        item = dict(word)
        if mode in {"hinglish", "auto"}:
            item["text"] = romanize_hindi_word(item["text"])
        item["text"] = clean_creator_word(item["text"])
        converted.append(item)
    return converted


def capitalize_first_word(text: str) -> str:
    """Capitalize the first alphabetic character only."""
    if not text:
        return text
    chars = list(text)
    for i, char in enumerate(chars):
        if char.isalpha():
            chars[i] = char.upper()
            break
    return "".join(chars)


def format_caption_lines(words: list, template: dict) -> str:
    """Format words into lines strictly using template's words_per_line and max_lines."""
    clean_words = [str(w).strip() for w in words if str(w).strip()]
    if not clean_words:
        return ""
    max_lines = max(1, int(template.get("max_lines", 2)))
    if max_lines == 1 or len(clean_words) <= 1:
        return " ".join(clean_words)
    wpl = list(template.get("words_per_line") or [])
    if not wpl:
        wpl = [2, 1] if len(clean_words) == 3 else [max(1, len(clean_words) // 2), max(1, len(clean_words) - len(clean_words) // 2)]

    lines = []
    idx = 0
    for i, count in enumerate(wpl):
        if idx >= len(clean_words):
            break
        if i == len(wpl) - 1:
            lines.append(" ".join(clean_words[idx:]))
            idx = len(clean_words)
        else:
            remaining_lines = len(wpl) - (i + 1)
            take = min(count, len(clean_words) - idx)
            if (len(clean_words) - (idx + take)) < remaining_lines:
                take = max(1, len(clean_words) - idx - remaining_lines)
            lines.append(" ".join(clean_words[idx:idx + take]))
            idx += take
    if idx < len(clean_words):
        if lines:
            lines[-1] = lines[-1] + " " + " ".join(clean_words[idx:])
        else:
            lines.append(" ".join(clean_words[idx:]))
    return "\n".join(lines)


def partition_chunk_words(chunk: dict, template: dict) -> list[list[dict]]:
    """Partition a chunk's words into lines based on explicit newlines in chunk['text'] or template's words_per_line."""
    words = list(chunk.get("words", []) or [])
    if not words:
        raw_text = str(chunk.get("text", "")).strip()
        if raw_text:
            words = [{"text": w, "start": chunk.get("start", 0), "end": chunk.get("end", 0)} for w in raw_text.split()]
        else:
            return []
    max_lines = max(1, int(template.get("max_lines", 2)))
    if max_lines == 1 or len(words) <= 1:
        return [words]

    raw_text = str(chunk.get("text", "")).strip()
    if "\n" in raw_text:
        text_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        if len(text_lines) > 1:
            line_groups = []
            w_idx = 0
            for i, line in enumerate(text_lines):
                line_word_count = len(line.split())
                if i == len(text_lines) - 1:
                    line_groups.append(words[w_idx:])
                    w_idx = len(words)
                else:
                    take = min(line_word_count, len(words) - w_idx)
                    remaining = len(text_lines) - (i + 1)
                    if (len(words) - (w_idx + take)) < remaining:
                        take = max(1, len(words) - w_idx - remaining)
                    line_groups.append(words[w_idx:w_idx + take])
                    w_idx += take
            if w_idx < len(words):
                if line_groups:
                    line_groups[-1].extend(words[w_idx:])
                else:
                    line_groups.append(words[w_idx:])
            return [g for g in line_groups if g]

    wpl = list(template.get("words_per_line") or [])
    if not wpl:
        wpl = [2, 1] if len(words) == 3 else [max(1, len(words) // 2), max(1, len(words) - len(words) // 2)]

    line_groups = []
    w_idx = 0
    for i, count in enumerate(wpl):
        if w_idx >= len(words):
            break
        if i == len(wpl) - 1:
            line_groups.append(words[w_idx:])
            w_idx = len(words)
        else:
            remaining = len(wpl) - (i + 1)
            take = min(count, len(words) - w_idx)
            if (len(words) - (w_idx + take)) < remaining:
                take = max(1, len(words) - w_idx - remaining)
            line_groups.append(words[w_idx:w_idx + take])
            w_idx += take
    if w_idx < len(words):
        if line_groups:
            line_groups[-1].extend(words[w_idx:])
        else:
            line_groups.append(words[w_idx:])
    return [g for g in line_groups if g]


def transform_chunks_language(chunks, mode: str, template: dict | None = None) -> list:
    """Apply the selected output mode to caption words while preserving template line structure."""
    output = []
    for chunk in chunks:
        updated = dict(chunk)
        updated["words"] = maybe_romanize_words(chunk.get("words", []), mode)

        # Capitalize the actual first caption word, not only the joined text.
        if mode in {"hinglish", "auto"} and updated["words"]:
            first = updated["words"][0]["text"]
            updated["words"][0]["text"] = capitalize_first_word(first)

        tmpl = template or chunk.get("template") or get_template_object(chunk.get("template_id", "bold_white"))
        raw_text = str(chunk.get("text", "")).strip()
        if "\n" in raw_text:
            lines_of_words = partition_chunk_words(updated, tmpl)
            updated["text"] = "\n".join(" ".join(w["text"] for w in lw) for lw in lines_of_words)
        else:
            updated["text"] = format_caption_lines([w["text"] for w in updated["words"]], tmpl)
        output.append(updated)
    return output


# =========================================================
# HELPERS
# =========================================================


def cleanup_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if root.is_dir():
        matches = list(root.rglob("ffmpeg.exe"))
        if matches:
            return str(matches[0])

    raise FileNotFoundError("FFmpeg executable not found.")

def probe_video_dimensions(input_path: Path) -> tuple[int, int]:
    """Return the source video's real picture dimensions.

    ASS uses a virtual canvas. Using a fixed 1920x1080 canvas for a 9:16
    creator video makes captions far wider than the actual picture. Probe the
    source so exported captions use the correct portrait/landscape geometry.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        try:
            ffmpeg_path = find_ffmpeg()
            candidate = Path(ffmpeg_path).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
            if candidate.exists():
                ffprobe = str(candidate)
        except Exception:
            pass
    if not ffprobe:
        return 1920, 1080

    cmd = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", str(input_path),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        value = completed.stdout.strip().splitlines()[0]
        width, height = (int(x) for x in value.split("x", 1))
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass
    return 1920, 1080


def safe_ass_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 0
        secs += 1
    if secs >= 60:
        secs -= 60
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        hours += 1
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def ass_color(hex_color: str, alpha: int = 0) -> str:
    value = (hex_color or "#FFFFFF").strip().lstrip("#")
    if len(value) != 6 or not all(c in "0123456789abcdefABCDEF" for c in value):
        value = "FFFFFF"
    r, g, b = value[0:2], value[2:4], value[4:6]
    alpha = max(0, min(255, int(alpha)))
    return f"&H{alpha:02X}{b}{g}{r}"


def line_break_texts(words, max_chars_per_line: int, line_break_mode: str = "balanced") -> tuple[list[str], int]:
    """Return a balanced 1- or 2-line word split and its split point."""
    texts = [clean_creator_word(w) for w in words if clean_creator_word(w)]
    if not texts:
        return [], 0
    if str(line_break_mode or "balanced") == "first_word" and len(texts) > 1:
        return texts, 1
    if len(" ".join(texts)) <= max_chars_per_line:
        return texts, len(texts)

    best = None
    best_score = 10**9
    for split in range(1, len(texts)):
        left = " ".join(texts[:split])
        right = " ".join(texts[split:])
        if len(left) <= max_chars_per_line and len(right) <= max_chars_per_line:
            score = abs(len(left) - len(right))
            if score < best_score:
                best = (texts, split)
                best_score = score
    if best:
        return best

    # For a single very long word, keep it intact. It is safer than creating a 3rd line.
    first = []
    second = []
    length = 0
    for word in texts:
        add = len(word) + (1 if first else 0)
        if first and length + add > max_chars_per_line:
            second.append(word)
        else:
            first.append(word)
            length += add
    return texts if not second else (texts, len(first))


def wrap_caption(text: str, max_chars_per_line: int = 26, max_lines: int = 2) -> str:
    words = text.split()
    if not words:
        return ""
    max_lines = max(1, int(max_lines or 2))
    if max_lines == 1:
        # Never create a second line for templates designed as single-line captions.
        return " ".join(words)
    _, split = line_break_texts(words, max_chars_per_line)
    left = " ".join(words[:split])
    right = " ".join(words[split:])
    if not right:
        return left
    return left + r"\N" + right


def make_caption_chunks(segments, template: dict | None = None):
    """Create caption frames strictly from the selected template's word pattern.

    The template's ``chunk_words`` is the primary rule. Speech pauses and
    arbitrary duration limits are NOT allowed to split a frame. Word-level
    timestamps are used only to set the frame's start/end time.

    Example: a 3-word template produces 3-word frames; a 4-word template
    produces 4-word frames. A final remainder is kept as-is rather than being
    merged with the previous frame. This keeps every frame independently
    editable and makes the selected template's rhythm deterministic.
    """
    template = template or get_template_object("bold_white")
    chunk_words = max(1, int(template.get("chunk_words", 4)))
    all_words = []

    for segment in segments:
        seg_words = []
        for word in (getattr(segment, "words", None) or []):
            txt = (getattr(word, "word", "") or "").strip()
            start = getattr(word, "start", None)
            end = getattr(word, "end", None)
            if txt and start is not None and end is not None:
                seg_words.append({"text": txt, "start": float(start), "end": float(end)})

        # Fallback when word timestamps are unavailable.
        if not seg_words:
            raw_text = " ".join((getattr(segment, "text", "") or "").strip().split())
            if raw_text:
                raw_words = raw_text.split()
                seg_start = float(getattr(segment, "start", 0))
                seg_end = float(getattr(segment, "end", seg_start + 0.25))
                duration = max(seg_end - seg_start, 0.25)
                per_word = duration / max(len(raw_words), 1)
                for i, word in enumerate(raw_words):
                    seg_words.append({
                        "text": word,
                        "start": seg_start + i * per_word,
                        "end": seg_start + (i + 1) * per_word,
                    })
        all_words.extend(seg_words)

    all_words.sort(key=lambda w: (float(w["start"]), float(w["end"])))
    if not all_words:
        return []

    chunks = []
    # STRICT TEMPLATE RHYTHM: exactly chunk_words per frame whenever
    # enough words exist across the continuous word stream.
    for offset in range(0, len(all_words), chunk_words):
        group = all_words[offset:offset + chunk_words]
        if not group:
            continue
        start = float(group[0]["start"])
        end = float(group[-1]["end"])
        if end <= start:
            end = start + 0.05
        text = format_caption_lines([w["text"] for w in group], template)
        chunks.append({
            "start": start,
            "end": end,
            "text": text,
            "words": list(group),
            "template_id": template.get("id", "bold_white"),
            "pattern_words": chunk_words,
            "pattern_max_chars": int(template.get("max_chars", 48)),
        })

    # Prevent accidental overlap between neighbouring frames without changing
    # their word membership.
    final = []
    for i, chunk in enumerate(chunks):
        if i + 1 < len(chunks):
            next_start = float(chunks[i + 1]["start"])
            if chunk["end"] > next_start:
                chunk["end"] = next_start
        if chunk["end"] <= chunk["start"]:
            chunk["end"] = chunk["start"] + 0.05
        final.append(chunk)
    return final


# =========================================================
# ASS STYLE RENDERING
# =========================================================


# =========================================================
# FINAL RENDER STYLE ENGINE
# =========================================================
# IMPORTANT: the editor preview is the source of truth for template choice.
# The export renderer uses the same CAPTION_TEMPLATES definitions used by the
# original V6 exporter. We deliberately do NOT create a second "template map"
# here: that was the reason edited exports changed appearance.

RENDER_MAX_WORDS = 6
RENDER_MAX_CHARS = 48


def _split_words_for_render(words, max_words=RENDER_MAX_WORDS, max_chars=RENDER_MAX_CHARS):
    """Split ONLY an over-long edited caption; never merge neighbouring chunks."""
    clean = [w for w in (words or []) if str(w.get('text', '')).strip()]
    if not clean:
        return []
    groups, current = [], []
    for word in clean:
        candidate = current + [word]
        chars = len(' '.join(str(w.get('text', '')).strip() for w in candidate))
        if current and (len(candidate) > max_words or chars > max_chars):
            groups.append(current)
            current = [word]
        else:
            current = candidate
    if current:
        groups.append(current)
    return groups


def prepare_render_chunks(chunks, template=None):
    """Keep the user's original caption chunks intact.

    A normal caption (including a 3-word or 4-word caption) remains ONE render event.
    Only a caption that became too long after editing is split into smaller
    chunks. Splits stay inside that caption's own time range, so captions are
    never accidentally merged together.
    """
    prepared = []
    template = template or get_template_object("bold_white")
    default_words = max(6, int(template.get("chunk_words", RENDER_MAX_WORDS)) * 2)
    max_lines = max(1, int(template.get("max_lines", 2)))
    default_chars = max(30, int(template.get("max_chars", RENDER_MAX_CHARS))) * max_lines
    for chunk in chunks or []:
        words = chunk.get('words', []) or []
        max_words = max(default_words, int(chunk.get("pattern_words") or len(words)))
        max_chars = max(default_chars, int(chunk.get("pattern_max_chars") or default_chars))
        groups = _split_words_for_render(words, max_words=max_words, max_chars=max_chars)
        if not groups:
            continue
        if len(groups) == 1:
            copy = dict(chunk)
            copy['words'] = list(groups[0])
            raw_text = str(chunk.get('text', '')).strip()
            if '\n' in raw_text and len(raw_text.split()) == len(groups[0]):
                copy['text'] = raw_text
            else:
                copy['text'] = format_caption_lines([w.get('text', '') for w in groups[0]], template)
            prepared.append(copy)
            continue

        chunk_start = float(chunk.get('start', 0))
        chunk_end = max(chunk_start + 0.05, float(chunk.get('end', chunk_start + 0.5)))
        for gi, group in enumerate(groups):
            gs = max(chunk_start, float(group[0].get('start', chunk_start)))
            ge = min(chunk_end, float(group[-1].get('end', chunk_end)))
            if ge <= gs:
                span = max(0.05, chunk_end - chunk_start) / len(groups)
                gs = chunk_start + gi * span
                ge = chunk_start + (gi + 1) * span if gi + 1 < len(groups) else chunk_end
            prepared.append({
                'id': f"{chunk.get('id', len(prepared)+1)}-{gi+1}",
                'start': gs,
                'end': max(gs + 0.05, ge),
                'text': format_caption_lines([w.get('text', '') for w in group], template),
                'words': list(group),
                'template': template,
                'template_id': template.get('id', 'bold_white'),
            })
    return prepared



def _effective_export_font_size(size) -> int:
    try:
        val = float(size)
    except (TypeError, ValueError):
        val = 64.0
    return max(24, min(160, round(val)))


def template_display_text(text: str, template: dict) -> str:
    value = str(text or "")
    mode = str(template.get("text_case", "sentence"))
    if mode == "upper":
        return value.upper()
    if mode == "lower":
        return value.lower()
    return value


def render_highlighted_text(chunk: dict, active_index: int, template: dict,
                            span_size: int = 54, strong_size: int = 84, is_glow_layer: bool = False) -> str:
    """Render one complete caption chunk while changing only the active word color."""
    lines_of_words = partition_chunk_words(chunk, template)
    if not lines_of_words:
        return ""

    line1_color = ass_color(template.get('line1_color', template.get('text_color', '#FFFFFF')))
    line2_color = ass_color(template.get('line2_color', template.get('text_color', '#FFFFFF')))
    highlight_colour = ass_color(template.get('highlight_color', '#FFE600'))
    glow_col = ass_color(template.get('glow_color', template.get('text_color', '#FFFFFF')))

    if is_glow_layer:
        line1_color = glow_col
        line2_color = glow_col
        highlight_colour = glow_col

    global_idx = 0
    line_strings = []
    for line_idx, line_words in enumerate(lines_of_words):
        is_first = (line_idx == 0 and len(lines_of_words) > 1)
        font_sz = span_size if is_first else strong_size
        default_col = line1_color if is_first else line2_color

        rendered_words = []
        for word in line_words:
            safe = safe_ass_text(template_display_text(word.get('text', ''), template))
            if global_idx == active_index:
                hl = ass_color('#FFFFFF') if default_col == highlight_colour and not is_glow_layer else highlight_colour
                rendered_words.append('{' + f'\\1c{hl}' + '}' + safe + '{' + f'\\1c{default_col}' + '}')
            else:
                rendered_words.append(safe)
            global_idx += 1

        line_styled = "{" + f"\\fs{font_sz}\\1c{default_col}" + "}" + " ".join(rendered_words)
        line_strings.append(line_styled)

    return r"\N".join(line_strings)


def _reference_canvas(video_width: int, video_height: int) -> tuple[int, int]:
    """Return a predictable ASS design canvas matching the source orientation."""
    w, h = max(1, int(video_width)), max(1, int(video_height))
    if h > w:
        return 1080, max(1080, round(1080 * h / w))
    if w > h:
        return max(1080, round(1080 * w / h)), 1080
    return 1080, 1080


def write_ass(chunks, out_path: Path, font_size: int, position_percent: int, style: dict,
              video_width: int = 1920, video_height: int = 1080, template: dict | None = None) -> None:
    """Render captions strictly from the canonical template definition."""
    source_width = max(1, int(video_width))
    source_height = max(1, int(video_height))
    canvas_width, canvas_height = _reference_canvas(source_width, source_height)
    template = template or style or get_template_object("bold_white")
    tmpl_id = str(template.get('id', 'bold_white'))
    position_percent = max(8, min(92, int(position_percent)))

    # On a standard canvas, scale font sizes from the canonical template definition
    scale_canvas = canvas_width / 720.0
    user_multiplier = max(0.6, min(1.6, float(font_size) / 54.0))

    native_size = float(template.get("font_size", 58) or 58)
    strong_size = _effective_export_font_size(native_size * scale_canvas * user_multiplier)

    span_scale = float(template.get("span_scale", 1.0))
    if int(template.get("max_lines", 2)) > 1 and span_scale < 0.99:
        span_size = _effective_export_font_size(strong_size * span_scale)
    else:
        span_size = strong_size

    effective_size = strong_size

    base_y = round(canvas_height * (position_percent / 100.0))
    export_border_style = int(template.get("border_style", 1) or 1)
    scale_stroke = canvas_width / 720.0

    is_glow = bool(template.get("glow", False))
    glow_color = template.get("glow_color", template.get("text_color", "#FFFFFF"))
    glow_size = float(template.get("glow_size", 8))

    if export_border_style == 3:
        # Bounding box / card style (black_box, white_box, news_ticker, editing_skool, liquid_glass, red_black_punch)
        export_outline_width = max(8, round(10 * scale_stroke))
        bg_opacity = int(template.get('background_opacity', 90) or 90)
        bg_opacity = max(20, min(100, bg_opacity))
        bg_alpha = round(255 * (100 - bg_opacity) / 100)
        bg_hex = template.get('background_color', '#000000')
        box_colour = ass_color(bg_hex, bg_alpha)
        box_outline_colour = box_colour
        raw_shadow = float(template.get('shadow_distance', template.get('shadow', 0)) or 0)
        if raw_shadow > 0:
            shadow_width = max(1, round(raw_shadow * scale_stroke))
            back_colour = ass_color(template.get('shadow_color', '#000000'))
        else:
            shadow_width = 0
            back_colour = "&H00000000"
    else:
        # Outline + Shadow style
        raw_outline = float(template.get('outline_width', 0) or 0)
        if raw_outline > 0:
            export_outline_width = max(1, round(raw_outline * scale_stroke))
            box_outline_colour = ass_color(template.get('outline_color', '#000000'))
        else:
            export_outline_width = 0
            box_outline_colour = "&H00000000"

        raw_shadow = float(template.get('shadow_distance', template.get('shadow', 0)) or 0)
        if raw_shadow > 0:
            shadow_width = max(1, round(raw_shadow * scale_stroke))
            back_colour = ass_color(template.get('shadow_color', '#000000'))
        else:
            shadow_width = 0
            back_colour = "&H00000000"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {canvas_width}
PlayResY: {canvas_height}
ScaledBorderAndShadow: yes
WrapStyle: 2
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{_ass_font_name(template)},{effective_size},{ass_color(template['text_color'])},{ass_color(template['text_color'])},{box_outline_colour},{back_colour},{-1 if template.get('bold') else 0},{1 if template.get('italic') else 0},0,0,100,100,{float(template.get('letter_spacing', 0)):.2f},0,{export_border_style},{export_outline_width},{shadow_width},5,0,0,0,1
Style: Glow,{_ass_font_name(template)},{effective_size},{ass_color(glow_color)},{ass_color(glow_color)},{ass_color(glow_color)},{ass_color(glow_color)},{-1 if template.get('bold') else 0},{1 if template.get('italic') else 0},0,0,100,100,{float(template.get('letter_spacing', 0)):.2f},0,1,{max(2, round(glow_size * scale_stroke * 0.6))},0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    animation = str(template.get("animation", "pop"))

    lines = [header]
    for chunk in (chunks or []):
        words = chunk.get('words', []) or []
        if not words and not chunk.get('text'):
            continue
        lines_of_words = partition_chunk_words(chunk, template)
        if not lines_of_words:
            continue

        if len(lines_of_words) == 1:
            line_col = ass_color(template.get('line1_color', template['text_color']))
            txt = safe_ass_text(" ".join(template_display_text(w.get('text', ''), template) for w in lines_of_words[0]))
            display_text = "{" + f"\\fs{strong_size}\\1c{line_col}" + "}" + txt
            display_glow = "{" + f"\\fs{strong_size}\\1c{ass_color(glow_color)}" + "}" + txt
        else:
            left_col = ass_color(template.get('line1_color', template['text_color']))
            right_col = ass_color(template.get('line2_color', template['text_color']))
            txt_left = safe_ass_text(" ".join(template_display_text(w.get('text', ''), template) for w in lines_of_words[0]))
            txt_right = safe_ass_text(" ".join(template_display_text(w.get('text', ''), template) for w in lines_of_words[1]))
            display_text = ("{" + f"\\fs{span_size}\\1c{left_col}" + "}" + txt_left +
                            r"\N{" + f"\\fs{strong_size}\\1c{right_col}" + "}" + txt_right)
            display_glow = ("{" + f"\\fs{span_size}\\1c{ass_color(glow_color)}" + "}" + txt_left +
                            r"\N{" + f"\\fs{strong_size}\\1c{ass_color(glow_color)}" + "}" + txt_right)

        line_count = max(1, display_text.count(r"\N") + 1)
        estimated_half_h = max(1, round(effective_size * line_count * max(0.38, float(template.get("line_height", 0.90)) * 0.55)))
        margin = max(12, round(canvas_height * 0.012))
        safe_y = max(estimated_half_h + margin, min(base_y, canvas_height - estimated_half_h - margin))
        start = ass_time(chunk['start'])
        end = ass_time(chunk['end'])

        # Stylish, modern animations matching short-form creator video editors
        if animation == "slide":
            pos_tag = f"{{\\an5\\move({canvas_width//2},{safe_y+40},{canvas_width//2},{safe_y},0,150)\\fad(90,60)}}"
            pos_static = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
        elif animation == "pop":
            pos_tag = f"{{\\an5\\pos({canvas_width//2},{safe_y})\\fscx82\\fscy82\\t(0,90,\\fscx108\\fscy108)\\t(90,170,\\fscx100\\fscy100)}}"
            pos_static = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
        elif animation == "bounce":
            pos_tag = f"{{\\an5\\pos({canvas_width//2},{safe_y})\\fscx78\\fscy78\\t(0,100,\\fscx114\\fscy114)\\t(100,180,\\fscx95\\fscy95)\\t(180,250,\\fscx100\\fscy100)}}"
            pos_static = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
        elif animation == "scale_in":
            pos_tag = f"{{\\an5\\pos({canvas_width//2},{safe_y})\\fscx72\\fscy72\\fad(80,0)\\t(0,140,\\fscx100\\fscy100)}}"
            pos_static = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
        elif animation == "fade":
            pos_tag = f"{{\\an5\\pos({canvas_width//2},{safe_y})\\fad(120,90)}}"
            pos_static = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
        elif animation == "glow_pulse":
            pos_tag = f"{{\\an5\\pos({canvas_width//2},{safe_y})\\fscx96\\fscy96\\t(0,140,\\fscx104\\fscy104)\\t(140,280,\\fscx100\\fscy100)}}"
            pos_static = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
        else:
            pos_tag = f"{{\\an5\\pos({canvas_width//2},{safe_y})}}"
            pos_static = pos_tag

        glow_blur = max(4, round(glow_size * scale_stroke * 0.9))

        all_flat_words = [w for line in lines_of_words for w in line]
        if template.get('highlight') and len(all_flat_words) > 1:
            for idx, word in enumerate(all_flat_words):
                active_start = max(float(chunk['start']), float(word.get('start', chunk['start'])))
                next_start = float(all_flat_words[idx + 1].get('start', chunk['end'])) if idx + 1 < len(all_flat_words) else float(chunk['end'])
                active_end = min(float(chunk['end']), next_start)
                if active_end <= active_start:
                    continue
                tag_to_use = pos_tag if abs(active_start - float(chunk['start'])) < 0.03 else pos_static
                highlighted = render_highlighted_text(chunk, idx, template, span_size, strong_size, is_glow_layer=False)

                if is_glow:
                    glow_highlighted = render_highlighted_text(chunk, idx, template, span_size, strong_size, is_glow_layer=True)
                    # Layer 0: Glow aura
                    lines.append(f"Dialogue: 0,{ass_time(active_start)},{ass_time(active_end)},Glow,,0,0,0,,{tag_to_use}{{\\blur{glow_blur}}}{glow_highlighted}\n")
                    # Layer 1: Sharp text
                    lines.append(f"Dialogue: 1,{ass_time(active_start)},{ass_time(active_end)},Default,,0,0,0,,{tag_to_use}{{\\blur0}}{highlighted}\n")
                else:
                    lines.append(f"Dialogue: 0,{ass_time(active_start)},{ass_time(active_end)},Default,,0,0,0,,{tag_to_use}{highlighted}\n")
        else:
            if is_glow:
                # Layer 0: Glow aura
                lines.append(f"Dialogue: 0,{start},{end},Glow,,0,0,0,,{pos_tag}{{\\blur{glow_blur}}}{display_glow}\n")
                # Layer 1: Sharp text
                lines.append(f"Dialogue: 1,{start},{end},Default,,0,0,0,,{pos_tag}{{\\blur0}}{display_text}\n")
            else:
                lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{pos_tag}{display_text}\n")

    out_path.write_text(''.join(lines), encoding='utf-8')

def _ass_font_name(style: dict) -> str:
    """Return a Windows/libass-friendly font family while preserving template intent."""
    name = str(style.get("font_name", "Arial"))
    aliases = {
        "Impact": "Impact",
        "Arial": "Arial",
        "Georgia": "Georgia",
        "Courier New": "Courier New",
    }
    return aliases.get(name, "Arial")




# =========================================================
# AUDIO NORMALIZATION
# =========================================================


def extract_audio_for_transcription(input_path: Path, workdir: Path) -> Path:
    """Normalize all source audio to mono 16 kHz PCM for more reliable recognition."""
    ffmpeg = find_ffmpeg()
    audio_path = workdir / "speech.wav"
    cmd = [
        ffmpeg, "-y", "-i", str(input_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(audio_path),
    ]
    completed = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True, errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            "Could not extract audio for transcription.\n" + completed.stderr[-5000:]
        )
    if not audio_path.exists() or audio_path.stat().st_size < 1024:
        raise RuntimeError("The uploaded video does not contain usable audio.")
    return audio_path


# =========================================================
# FFMPEG
# =========================================================


def run_ffmpeg(input_path: Path, ass_path: Path, output_path: Path, volume_percent: int = 100) -> None:
    ffmpeg = find_ffmpeg()
    volume_percent = max(0, min(200, int(volume_percent)))
    volume = volume_percent / 100.0

    cmd = [
        ffmpeg, "-y", "-i", str(input_path),
        "-vf", f"subtitles=filename='{ass_path.name}'",
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
    ]
    if volume_percent != 100:
        cmd += ["-af", f"volume={volume:.2f}"]
    cmd += [
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(output_path),
    ]

    completed = subprocess.run(cmd, cwd=str(ass_path.parent), capture_output=True, text=True, errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-6000:])


# =========================================================
# API
# =========================================================


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "model": MODEL_SIZE,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
    }


@app.get("/api/templates")
def templates_api():
    return {"templates": all_template_objects()}


@app.post("/api/caption")
async def caption_video(
    video: UploadFile = File(...),
    language: Optional[str] = Form(None),
    font_size: int = Form(54),
    position: str = Form("bottom"),
    position_percent: int = Form(78),
    template: str = Form("bold_white"),
    audio_volume: int = Form(100),
    hotwords: str = Form(""),
):
    """Upload + transcribe only. The browser then opens the Caption Editor."""
    if not video.filename:
        raise HTTPException(status_code=400, detail="Please choose a video file.")

    if template not in CAPTION_TEMPLATES:
        template = "bold_white"
    style = dict(CAPTION_TEMPLATES[template])

    if position not in {"top", "bottom"}:
        position = "bottom"
    try:
        position_percent = int(position_percent)
    except (TypeError, ValueError):
        position_percent = 78 if position == "bottom" else 18
    position_percent = max(10, min(90, position_percent))

    try:
        requested_size = int(font_size)
    except (TypeError, ValueError):
        requested_size = style["font_size"]
    font_size = style["font_size"] if requested_size == 54 else max(32, min(80, requested_size))

    try:
        audio_volume = int(audio_volume)
    except (TypeError, ValueError):
        audio_volume = 100
    audio_volume = max(0, min(200, audio_volume))

    workdir = Path(tempfile.mkdtemp(prefix="autocaption_editor_"))
    suffix = Path(video.filename).suffix.lower() or ".mp4"
    input_path = workdir / f"input{suffix}"

    try:
        total = 0
        with input_path.open("wb") as f:
            while chunk := await video.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_MB * 1024 * 1024:
                    raise HTTPException(status_code=413, detail=f"Video is too large. Maximum size is {MAX_UPLOAD_MB} MB.")
                f.write(chunk)

        audio_path = extract_audio_for_transcription(input_path, workdir)
        requested_mode = (language or "auto").strip().lower()
        if requested_mode not in {"auto", "hinglish", "hi", "en"}:
            requested_mode = "auto"

        transcribe_kwargs = {
            "beam_size": 8,
            "best_of": 5,
            "patience": 1.2,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "no_speech_threshold": 0.55,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 350, "speech_pad_ms": 180},
            "condition_on_previous_text": True,
            "word_timestamps": True,
            "multilingual": True,
            "language_detection_segments": 5,
            "language_detection_threshold": 0.35,
            "initial_prompt": (
                "Indian creator speech. Hindi, English and Hinglish can be mixed. "
                "Keep English words in English. Recognize Hindi accurately. "
                "Do not translate. Preserve names, brands, slang, numbers and technical terms. "
                "Examples: Hello guys kese ho, Aaj hum ek important topic discuss karenge."
            ),
        }
        if hotwords.strip():
            transcribe_kwargs["hotwords"] = hotwords.strip()[:1000]
        if requested_mode in {"hinglish", "hi"}:
            # Hinglish means Hindi speech written with Latin letters, not English
            # translation. Force Hindi recognition first; otherwise Whisper can
            # auto-detect the speaker's audio as Telugu/another Indic language
            # and the caption pipeline receives the wrong script. English words
            # inside Hindi/Hinglish speech are still preserved by Whisper.
            transcribe_kwargs["language"] = "hi"
            transcribe_kwargs["multilingual"] = False
        elif requested_mode == "en":
            transcribe_kwargs["language"] = "en"
            transcribe_kwargs["multilingual"] = False

        segments_iter, info = model.transcribe(str(audio_path), **transcribe_kwargs)
        segments = list(segments_iter)
        if not segments:
            raise HTTPException(status_code=422, detail="No speech was detected in the video.")

        template_object = get_template_object(template)
        tmpl_pos = template_object.get("position", "lower")
        default_pos = 50 if tmpl_pos == "center" else (18 if tmpl_pos == "top" else 78)
        if position_percent == 78 and tmpl_pos != "lower":
            position_percent = default_pos
        chunks = make_caption_chunks(segments, template_object)
        if not chunks:
            raise HTTPException(status_code=422, detail="Could not create captions.")
        if requested_mode in {"auto", "hinglish"}:
            chunks = transform_chunks_language(chunks, requested_mode, template_object)

        # Make JSON-safe copies for the editor.
        editor_chunks = []
        for i, chunk in enumerate(chunks):
            editor_chunks.append({
                "id": i + 1,
                "start": round(float(chunk["start"]), 3),
                "end": round(float(chunk["end"]), 3),
                "text": str(chunk.get("text", "")),
                "words": [
                    {"text": str(w.get("text", "")), "start": round(float(w.get("start", 0)), 3), "end": round(float(w.get("end", 0)), 3)}
                    for w in chunk.get("words", [])
                ],
                "template": template_object,
                "template_id": template,
                "pattern_words": len(chunk.get("words", []) or []),
                "pattern_max_chars": int(template_object.get("max_chars", 28)),
                "pattern_max_lines": int(template_object.get("max_lines", 2)),
            })

        session_id = uuid.uuid4().hex
        EDITOR_SESSIONS[session_id] = {
            "dir": str(workdir),
            "input": str(input_path),
            "filename": video.filename,
            "chunks": editor_chunks,
            "template": template_object,
            "template_id": template,
            "font_size": font_size,
            "position_percent": position_percent,
            "audio_volume": audio_volume,
            "language": requested_mode,
            "detected_language": getattr(info, "language", "unknown") or "unknown",
        }

        return {
            "session_id": session_id,
            "source_url": f"/api/editor/source/{session_id}",
            "chunks": editor_chunks,
            "template": template_object,
            "font_size": font_size,
            "position_percent": position_percent,
            "audio_volume": audio_volume,
            "detected_language": getattr(info, "language", "unknown") or "unknown",
            "mode": requested_mode,
        }
    except HTTPException:
        cleanup_dir(str(workdir))
        raise
    except FileNotFoundError:
        cleanup_dir(str(workdir))
        raise HTTPException(status_code=500, detail="FFmpeg is not installed or not available on PATH.")
    except Exception as exc:
        cleanup_dir(str(workdir))
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
    finally:
        await video.close()


@app.get("/api/editor/source/{session_id}")
def editor_source(session_id: str):
    session = EDITOR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Editor session expired. Please process the video again.")
    path = Path(session["input"])
    if not path.exists():
        EDITOR_SESSIONS.pop(session_id, None)
        raise HTTPException(status_code=404, detail="Source video is no longer available.")
    media_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
    return FileResponse(
        path,
        media_type=media_type,
        filename=session["filename"],
        headers={"Accept-Ranges": "bytes"}
    )


def _safe_editor_chunks(raw_chunks, original_chunks, canonical_template=None):
    """Validate editor data while preserving real Whisper word timestamps.

    If a user fixes a word without changing the word count, the original
    Whisper timing is retained. If the caption duration is changed, timings
    are scaled into the new duration. Only when words are added/removed do we
    fall back to proportional timing.
    """
    if not isinstance(raw_chunks, list):
        raise HTTPException(status_code=400, detail="Invalid caption list.")
    result = []
    originals = {int(c.get("id", i + 1)): c for i, c in enumerate(original_chunks or []) if isinstance(c, dict)}
    for idx, raw in enumerate(raw_chunks[:600]):
        if not isinstance(raw, dict):
            continue
        try:
            start = max(0.0, float(raw.get("start", 0)))
            end = max(start + 0.05, float(raw.get("end", start + 0.5)))
        except (TypeError, ValueError):
            continue
        raw_text = str(raw.get("text", "")).strip()
        lines = [" ".join(l.split()) for l in raw_text.splitlines() if l.strip()]
        if not lines:
            continue
        text = "\n".join(lines)
        words = (" ".join(lines)).split()
        raw_words = raw.get("words") if isinstance(raw.get("words"), list) else []
        source_words = raw_words if raw_words else originals.get(int(raw.get("id", idx + 1)), {}).get("words", [])
        timed_words = []
        if len(source_words) == len(words) and source_words:
            try:
                old_start = float(source_words[0].get("start", start))
                old_end = float(source_words[-1].get("end", end))
                old_duration = max(0.001, old_end - old_start)
                duration = end - start
                for wi, word in enumerate(words):
                    os_ = float(source_words[wi].get("start", old_start))
                    oe_ = float(source_words[wi].get("end", old_end))
                    rs = max(0.0, min(1.0, (os_ - old_start) / old_duration))
                    re_ = max(rs, min(1.0, (oe_ - old_start) / old_duration))
                    timed_words.append({"text": word, "start": start + rs * duration, "end": start + re_ * duration})
            except (TypeError, ValueError, AttributeError):
                timed_words = []
        if not timed_words:
            duration = max(0.05, end - start)
            per = duration / max(len(words), 1)
            timed_words = [{"text": word, "start": start + wi * per, "end": end if wi == len(words) - 1 else start + (wi + 1) * per} for wi, word in enumerate(words)]
        original = originals.get(int(raw.get("id", idx + 1)), {}) if isinstance(raw.get("id", idx + 1), (int, float, str)) else {}
        tmpl = canonical_template or original.get("template") or raw.get("template") or get_template_object("bold_white")
        tid = tmpl.get("id") or "bold_white"

        if "\n" not in text and int(tmpl.get("max_lines", 2)) > 1 and len(words) > 1:
            text = format_caption_lines(words, tmpl)

        result.append({
            "id": idx + 1,
            "start": start,
            "end": end,
            "text": text,
            "words": timed_words,
            "template": tmpl,
            "template_id": tid,
            "pattern_words": max(1, int(raw.get("pattern_words") or original.get("pattern_words") or (tmpl.get("chunk_words") if tmpl else len(words)))),
            "pattern_max_chars": max(12, int(raw.get("pattern_max_chars") or original.get("pattern_max_chars") or (tmpl.get("max_chars") if tmpl else 28))),
            "pattern_max_lines": max(1, int(raw.get("pattern_max_lines") or original.get("pattern_max_lines") or (tmpl.get("max_lines") if tmpl else 2))),
        })
    result.sort(key=lambda x: x["start"])
    return result


@app.post("/api/editor/render")
async def render_editor(request: dict):
    session_id = str(request.get("session_id", ""))
    session = EDITOR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Editor session expired. Please process the video again.")

    try:
        session_template = session.get("template")
        template_id = str(session.get("template_id") or (session_template.get("id") if isinstance(session_template, dict) else "bold_white"))
        template = session_template if isinstance(session_template, dict) else get_template_object(template_id)
        style = dict(template)

        chunks = _safe_editor_chunks(request.get("chunks", []), session.get("chunks", []), template)
        if not chunks:
            raise HTTPException(status_code=400, detail="Add at least one caption before exporting.")

        render_chunks = prepare_render_chunks(chunks, template)

        try:
            req_size = int(request.get("font_size", 0))
            font_size = max(32, min(80, req_size)) if req_size > 0 else int(session.get("font_size", style["font_size"]))
        except (TypeError, ValueError):
            font_size = int(session.get("font_size", style["font_size"]))

        try:
            req_pos = int(request.get("position_percent", 0))
            position_percent = max(10, min(90, req_pos)) if req_pos > 0 else int(session.get("position_percent", 78))
        except (TypeError, ValueError):
            position_percent = int(session.get("position_percent", 78))

        tmpl_pos = template.get("position", "lower")
        default_pos = 50 if tmpl_pos == "center" else (18 if tmpl_pos == "top" else 78)
        if position_percent == 78 and tmpl_pos != "lower":
            position_percent = default_pos

        try:
            audio_volume = max(0, min(200, int(request.get("audio_volume", session.get("audio_volume", 100)))))
        except (TypeError, ValueError):
            audio_volume = int(session.get("audio_volume", 100))

        workdir = Path(session["dir"])
        input_path = Path(session["input"])
        subtitle_path = workdir / "edited-captions.ass"
        output_path = workdir / f"captioned-edited-{uuid.uuid4().hex[:8]}.mp4"
        video_width, video_height = probe_video_dimensions(input_path)
        write_ass(render_chunks, subtitle_path, font_size, position_percent, style, video_width, video_height, template)
        run_ffmpeg(input_path, subtitle_path, output_path, audio_volume)

        filename = Path(session["filename"]).stem + "-edited.mp4"
        return FileResponse(output_path, media_type="video/mp4", filename=filename)
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="FFmpeg is not installed or not available on PATH.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}")


app.mount(
    "/",
    StaticFiles(directory=STATIC_DIR, html=True),
    name="static",
)


if __name__ == "__main__":
    import socket
    import sys
    import uvicorn

    def find_available_port(start_port: int = 8000, max_attempts: int = 20) -> int:
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port))
                    return port
                except OSError:
                    continue
        return start_port

    target_port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        target_port = int(sys.argv[1])
    else:
        try:
            target_port = int(os.getenv("PORT", "8000"))
        except ValueError:
            target_port = 8000

    chosen_port = find_available_port(target_port)
    if chosen_port != target_port:
        print(f"[AutoCaption] Notice: Port {target_port} is already in use. Binding to port {chosen_port} instead.")

    print(f"\n=======================================================")
    print(f"  AutoCaption AI is running at: http://127.0.0.1:{chosen_port}")
    print(f"  Also available at: http://localhost:{chosen_port}")
    print(f"=======================================================\n")
    uvicorn.run(app, host="0.0.0.0", port=chosen_port)
