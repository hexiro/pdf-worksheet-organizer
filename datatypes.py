from __future__ import annotations


import typing as t

import pikepdf

if t.TYPE_CHECKING:
    import fitz as pymupdf
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

# (x0, y0, x1, y1, "word", block_no, line_no, word_no)
# https://pymupdf.readthedocs.io/en/latest/textpage.html#TextPage.extractWORDS
MuWord: t.TypeAlias = "tuple[float, float, float, float, str, int, int, int]"


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


class PdfImage(t.NamedTuple):
    id: int
    stream: pikepdf.Stream
    bounding_box: pymupdf.IRect

  

    def as_pil_image(self) -> Image.Image:
        return pikepdf.PdfImage(self.stream).as_pil_image()


class PdfWord(t.NamedTuple):
    word: str
    bounding_box: pymupdf.IRect
    block_num: int
    line_num: int
    word_num: int


PdfText: t.TypeAlias = "list[PdfWord]"
PdfImages: t.TypeAlias = "list[PdfImage]"


class PdfPage(t.NamedTuple):
    text: PdfText
    images: PdfImages

    @property
    def image_streams(self) -> t.Generator[pikepdf.Stream, None, None]:
        for image in self.images:
            yield image.stream


class PdfFile(t.NamedTuple):
    pages: list[PdfPage]


class PdfNumberedPage(PdfPage):
    @property
    def elements(self) -> t.Generator[t.Union[PdfImage, PdfWord], None, None]:
        yield from self.images
        yield from self.text


class PdfNumberedFile(t.NamedTuple):
    pages: list[PdfNumberedPage]
