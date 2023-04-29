from __future__ import annotations

import re
import typing as t
from dataclasses import dataclass


import pikepdf
import fitz as pymupdf
from PIL import ImageFont

if t.TYPE_CHECKING:
    import io
    from PIL import Image

# https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_image_info
MuImage = t.TypedDict(
    "MuImage",
    {
        "number": int,
        "bbox": tuple[int, int, int, int],
        "transform": tuple[int, int, int, int],
        "width": int,
        "height": int,
        "colorspace": int,
        "cs-name": str,
        "xres": int,
        "yres": int,
        "bpc": int,
        "size": int,
        "digest": bytes,
        "xref": int,
    },
)


# https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
class MuTextSpan(t.TypedDict):
    bbox: tuple[float, float, float, float]  # span rectangle, type: rect_like
    origin: tuple[float, float]  # the first character’s origin, type: point_like
    font: str  # font name
    ascender: float  # ascender of the font
    descender: float  # descender of the font
    size: float  # font size
    flags: int  # font characteristics
    color: int  # text color in sRGB format
    text: str  #  text


# https://pymupdf.readthedocs.io/en/latest/textpage.html#line-dictionary
class MuTextLine(t.TypedDict):
    bbox: list[float]  # line rectangle, type: rect_like
    wmode: int  # writing mode: 0 = horizontal, 1 = vertical
    # writing direction, type: point_like, unit vector dir = (cosine, sine) of the angle, which the text has relative to the x-axis
    dir: tuple[float, float]
    spans: list[MuTextSpan]  # list of span dictionaries


# https://pymupdf.readthedocs.io/en/latest/textpage.html#block-dictionaries
class MuTextBlock(t.TypedDict):
    number: int  # block count
    type: t.Literal[0]  # always 0 in this case, 0 = text, 1 = image
    bbox: tuple[float, float, float, float]  # image bbox on page, type: rect_like
    lines: list[MuTextLine]  # list of text line dictionaries


# https://pymupdf.readthedocs.io/en/latest/textpage.html#structure-of-dictionary-outputs
class MuTextDict(t.TypedDict):
    width: float  # width of the clip rectangle (float)
    height: float  # height of the clip rectangle (float)
    blocks: list[MuTextBlock]  # list of block dictionaries


PdfText: t.TypeAlias = "list[PdfWord]"
PdfImages: t.TypeAlias = "list[PdfImage]"


# output of pytesseract.image_to_data w/ output_type = Output.DICT
# all parallel lists
class OcrImageData(t.TypedDict):
    level: list[int]
    page_num: list[int]
    block_num: list[int]
    par_num: list[int]
    line_num: list[int]
    word_num: list[int]
    left: list[int]
    top: list[int]
    width: list[int]
    height: list[int]
    conf: list[int]  # [0-100]
    text: list[str]


class PdfFont(t.NamedTuple):
    name: str
    encoding: str
    buffer: io.BytesIO

    def as_pil_font(self, font_size: int) -> ImageFont.FreeTypeFont | None:
        # true type font encodings:
        # * "unic" (Unicode)
        # * "symb" (Microsoft Symbol)
        # * "ADOB" (Adobe Standard)
        # * "ADBE" (Adobe Expert)
        # * "ADBC" (Adobe Custom)
        # * "armn" (Apple Roman)
        # * "sjis" (Shift JIS)
        # * "gb  " (PRC)
        # * "big5"
        # * "wans" (Extended Wansung)
        # * "joha" (Johab)
        # * "lat1" (Latin-1)

        font_encoding: str
        if self.encoding == "WinAnsiEncoding":
            font_encoding = "lat1"
        elif self.encoding == "MacRomanEncoding":
            font_encoding = "armn"
        else:
            font_encoding = self.encoding
        try:
            return ImageFont.truetype(font=self.buffer.getvalue(), size=font_size, encoding=font_encoding)
        except UnicodeDecodeError:
            return None

    def as_pymupdf_font(self) -> pymupdf.Font:
        return pymupdf.Font(fontname=self.name, fontbuffer=self.buffer.getvalue())


@dataclass(frozen=True)
class PdfImage:
    id: int
    stream: pikepdf.Stream
    bounding_box: pymupdf.Rect

    def as_pil_image(self) -> Image.Image:
        return pikepdf.PdfImage(self.stream).as_pil_image()


@dataclass(frozen=True)
class PdfWord:
    text: str
    font: str
    font_size: float
    bounding_box: pymupdf.Rect
    origin: pymupdf.Point


class PdfPage(t.NamedTuple):
    text: PdfText
    images: PdfImages

    @property
    def image_streams(self) -> t.Generator[pikepdf.Stream, None, None]:
        for image in self.images:
            yield image.stream


class PdfFile(t.NamedTuple):
    pages: list[PdfPage]


@dataclass(frozen=True)
class PdfNumberedImage(PdfImage):
    word: str
    number_bounding_box: pymupdf.Rect


@dataclass(frozen=True)
class PdfNumberedWord(PdfWord):
    match: re.Match[str]


# bounding_box in PdfImage now refers to the bounding box of the number instead of the whole image
class PdfNumberedPage(t.NamedTuple):
    elements: list[PdfNumberedWord | PdfNumberedImage]


class PdfNumberedFile(t.NamedTuple):
    pages: list[PdfNumberedPage]

    @property
    def questions_count(self) -> int:
        return sum(len(page.elements) for page in self.pages)
