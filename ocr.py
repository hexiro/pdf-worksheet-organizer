from __future__ import annotations
import pathlib

import pytesseract

import typing as t

from datatypes import OcrImageData

if t.TYPE_CHECKING:
    from datatypes import PdfImage


def image_to_text(image: PdfImage) -> OcrImageData:
    pil_image = image.as_pil_image()
    image_data: OcrImageData = pytesseract.image_to_data(pil_image, lang="eng", output_type=pytesseract.Output.DICT)
    return image_data
