import io, rich
import random
import pathlib

import typing as t

from PIL import Image, ImageDraw


import pikepdf

# from paddleocr import PaddleOCR

import fitz as pymupdf


def ocr(image: Image.Image) -> None:
    import pytesseract

    return pytesseract.image_to_string(image)


def image_name_as_int(image_name: str) -> int:
    image_name = image_name.removeprefix("/")
    image_name = image_name.removeprefix("Image")
    if not image_name.isdigit():
        raise ValueError(f"Image name {image_name} is not a digit")
    return int(image_name)


def pdf_file_to_pdf_streams(pdf_file: pathlib.Path) -> dict[str, pikepdf.Stream]:
    pdf = pikepdf.open(pdf_file)

    image_name_to_stream: dict[str, pikepdf.Stream] = {}  # type: ignore

    for page in pdf.pages:
        image_name_to_stream.update(page.images)

    return image_name_to_stream
  


def pdf_file_to_image_dimensions(pdf_file: pathlib.Path) -> dict[str, pymupdf.IRect]:
    pdf = pymupdf.Document(pdf_file)
    pages: t.Generator[pymupdf.Page, None, None] = pdf.pages()

    image_name_to_dimensions: dict[str, pymupdf.IRect] = {}

    for page in pages:
        images: list[tuple] = page.get_images(full=True)

        for image in images:
            image_name = image[7]

            bounding_box: pymupdf.Rect = page.get_image_bbox(image)  # type: ignore
            rounded_bounding_box: pymupdf.IRect = bounding_box.round()

            image_name_to_dimensions[image_name] = rounded_bounding_box

    return image_name_to_dimensions




def main(pdf_file: pathlib.Path) -> None:
    image_name_to_stream = pdf_file_to_pdf_streams(pdf_file)
    image_name_to_dimensions = pdf_file_to_image_dimensions(pdf_file)

    rich.print(image_name_to_stream)
    rich.print(image_name_to_dimensions)


if __name__ == "__main__":
    file = pathlib.Path(__file__)
    in_dir = file.parent / "in"
    out_dir = file.parent / "out"

    in_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    pdf_files = list(in_dir.glob("*.pdf"))
    pdf_file = pdf_files[0]

    main(pdf_file)
