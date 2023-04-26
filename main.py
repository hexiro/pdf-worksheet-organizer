import io, rich
import random
import pathlib

import typing as t

import pikepdf
import fitz as pymupdf
from PIL import Image, ImageDraw

from datatypes import PdfImage, PdfPage, PdfFile


def ocr(image: Image.Image) -> None:
    import pytesseract

    return pytesseract.image_to_string(image)


def image_name_as_int(image_name: str) -> int:
    image_name = image_name.removeprefix("/")
    image_name = image_name.removeprefix("Image")
    if not image_name.isdigit():
        raise ValueError(f"Image name {image_name} is not a digit")
    return int(image_name)


def pdf_to_image_streams(pdf: pikepdf.Pdf) -> dict[int, pikepdf.Stream]:
    image_name_to_stream: dict[int, pikepdf.Stream] = {}  # type: ignore

    for page in pdf.pages:
        for image_name, image in page.images.items():
            image_name_int = image_name_as_int(image_name)
            image_name_to_stream[image_name_int] = image

    return image_name_to_stream


def pdf_to_image_ids_on_each_page(pdf: pikepdf.Pdf) -> list[list[int]]:
    images_on_each_page: list[list[int]] = []

    for page in pdf.pages:
        images_on_page: list[int] = []

        for image_name in page.images:
            image_id = image_name_as_int(image_name)
            images_on_page.append(image_id)

        images_on_each_page.append(images_on_page)

    return images_on_each_page


def pdf_to_image_dimensions(pdf: pymupdf.Document) -> dict[int, pymupdf.IRect]:
    pages: t.Generator[pymupdf.Page, None, None] = pdf.pages()
    image_id_to_dimensions: dict[int, pymupdf.IRect] = {}

    for page in pages:
        images: list[tuple] = page.get_images(full=True)

        for image in images:
            image_name = image[7]
            image_id = image_name_as_int(image_name)
            bounding_box: pymupdf.Rect = page.get_image_bbox(image)  # type: ignore
            rounded_bounding_box: pymupdf.IRect = bounding_box.round()
            image_id_to_dimensions[image_id] = rounded_bounding_box

    return image_id_to_dimensions


def convert_pdf_types_to_pdf_file(pike_pdf: pikepdf.Pdf, mu_pdf: pymupdf.Document) -> PdfFile:
    images_on_each_page = pdf_to_image_ids_on_each_page(pike_pdf)
    image_name_to_stream = pdf_to_image_streams(pike_pdf)
    image_name_to_dimensions = pdf_to_image_dimensions(mu_pdf)

    pdf_pages: list[PdfPage] = []

    for image_ids in images_on_each_page:
        pdf_images: list[PdfImage] = []

        for image_id in image_ids:
            image_stream = image_name_to_stream[image_id]
            image_dimensions = image_name_to_dimensions[image_id]

            pdf_image = PdfImage(
                id=image_id,
                stream=image_stream,
                bounding_box=image_dimensions,
            )

            pdf_images.append(pdf_image)

        pdf_page = PdfPage(images=pdf_images)
        pdf_pages.append(pdf_page)

    return PdfFile(pages=pdf_pages)


def main(pdf_path: pathlib.Path) -> None:
    pike_pdf = pikepdf.open(pdf_path)
    mu_pdf = pymupdf.Document(pdf_path)

    # pdf_file = convert_pdf_types_to_pdf_file(pike_pdf, mu_pdf)

    first_page: pymupdf.Page = next(mu_pdf.pages(start=0, stop=1))
    # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    text_data: tuple[float, float, float, float, str, int, int, int] = first_page.get_textpage().extractWORDS()

    bounding_box = pymupdf.IRect(*text_data[:4])
    word = text_data[4]
    block_num, line_num, word_num = text_data[5:8]

    


if __name__ == "__main__":
    file = pathlib.Path(__file__)
    in_dir = file.parent / "in"
    out_dir = file.parent / "out"

    in_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    pdf_files = list(in_dir.glob("*.pdf"))
    pdf_file = pdf_files[0]

    # TODO: keep working on pdf_file text logic
    # TODO: regex for text

    main(pdf_file)
