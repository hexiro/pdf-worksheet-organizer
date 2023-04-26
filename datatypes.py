from __future__ import annotations


import typing as t

import pikepdf

if t.TYPE_CHECKING:
    import fitz as pymupdf
    from PIL import Image


class PdfImage(t.NamedTuple):
    id: int
    stream: pikepdf.Stream
    bounding_box: pymupdf.IRect

    @property
    def top(self) -> int:
        return self.bounding_box.y0

    def as_pil_image(self) -> Image.Image:
        return pikepdf.PdfImage(self.stream).as_pil_image()


class PdfText(t.NamedTuple):
    text: str
    bounding_box: pymupdf.IRect
    block_num: int
    line_num: int
    word_num: int


class PdfPage(t.NamedTuple):
    text: list[PdfText]
    images: list[PdfImage]

    @property
    def image_streams(self) -> t.Generator[pikepdf.Stream, None, None]:
        for image in self.images:
            yield image.stream


class PdfFile(t.NamedTuple):
    pages: list[PdfPage]
