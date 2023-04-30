from __future__ import annotations

import contextlib

import fitz as pymupdf

from pdf_worksheet_organizer.datatypes import PdfFont

from PIL import ImageFont


def fonts_pil_font(fonts: list[PdfFont], font_size: int) -> ImageFont._Font:
    pil_font: ImageFont._Font | None = None
    for font in fonts:
        pil_font = font.as_pil_font(font_size)
        if pil_font:
            return pil_font
    return load_backup_font(font_size)


def load_backup_font(font_size: int) -> ImageFont._Font:
    attempt_to_load_fonts = [
        "Proxima Nova Font.otf",  # biased choice :)
        "arial.ttf",
        "times.ttf",
    ]

    for font_name in attempt_to_load_fonts:
        with contextlib.suppress(OSError):
            return ImageFont.truetype(font=font_name, size=font_size)

    return ImageFont.load_default()
