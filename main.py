import rich
import pathlib

import typing as t

import pikepdf
import fitz as pymupdf
from PIL import Image

from datatypes import PdfImage, PdfPage, PdfFile, PdfWord, PdfText, MuImage, MuWord


def ocr(image: Image.Image) -> None:
    import pytesseract

    return pytesseract.image_to_string(image)


def image_name_as_int(image_name: str) -> int:
    image_name = image_name.removeprefix("/")
    image_name = image_name.removeprefix("Image")
    if not image_name.isdigit():
        raise ValueError(f"Image name {image_name} is not a digit")
    return int(image_name)


def parse_pdf_text(mu_page: pymupdf.Page) -> PdfText:
    # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    text_data: list[MuWord] = mu_page.get_textpage().extractWORDS()
    pdf_text: PdfText = []

    for word_data in text_data:
        bounding_box = pymupdf.IRect(*word_data[:4])
        word = word_data[4]
        block_num, line_num, word_num = word_data[5:8]

        pdf_word = PdfWord(
            word=word,
            bounding_box=bounding_box,
            block_num=block_num,
            line_num=line_num,
            word_num=word_num,
        )
        pdf_text.append(pdf_word)

    return pdf_text


def load_page(page_num: int, pike_pdf: pikepdf.Pdf, mu_pdf: pymupdf.Document) -> tuple[pikepdf.Page, pymupdf.Page]:
    pike_page = pike_pdf.pages[page_num]
    mu_page = mu_pdf.load_page(page_num)
    return pike_page, mu_page


def load_images(pike_page: pikepdf.Page, mu_page: pymupdf.Page) -> tuple[dict[int, pikepdf.Stream], list[MuImage]]:
    pike_images = {image_name_as_int(k): v for k, v in pike_page.images.items()}
    mu_images: list[MuImage] = mu_page.get_image_info(xrefs=True)  # type: ignore
    return pike_images, mu_images


def parse_pdf_images(
    pike_images: dict[int, pikepdf.Stream],
    mu_images: list[MuImage],
) -> list[PdfImage]:
    pdf_images: list[PdfImage] = []

    for mu_image in mu_images:
        image_id = mu_image["xref"]
        image_dimensions = mu_image["bbox"]
        image_stream = pike_images[image_id]

        pdf_image = PdfImage(
            id=image_id,
            stream=image_stream,
            bounding_box=pymupdf.IRect(image_dimensions),
        )

        pdf_images.append(pdf_image)

    return pdf_images


def parse_page(
    page_num: int,
    pike_pdf: pikepdf.Pdf,
    mu_pdf: pymupdf.Document,
) -> PdfPage:
    pike_page, mu_page = load_page(page_num, pike_pdf, mu_pdf)
    pike_images, mu_images = load_images(pike_page, mu_page)

    pdf_images = parse_pdf_images(pike_images, mu_images)
    pdf_text = parse_pdf_text(mu_page)

    pdf_page = PdfPage(images=pdf_images, text=pdf_text)
    return pdf_page


def parse_pdf(pike_pdf: pikepdf.Pdf, mu_pdf: pymupdf.Document) -> PdfFile:
    page_count = len(pike_pdf.pages)

    pages: list[PdfPage] = []

    for page_num in range(page_count):
        page = parse_page(page_num, pike_pdf, mu_pdf)
        pages.append(page)

    pdf_file = PdfFile(pages=pages)
    return pdf_file


def main(pdf_path: pathlib.Path) -> None:
    pike_pdf = pikepdf.open(pdf_path)
    mu_pdf = pymupdf.Document(pdf_path)

    pdf_file = parse_pdf(pike_pdf, mu_pdf)
    rich.print(pdf_file)


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
