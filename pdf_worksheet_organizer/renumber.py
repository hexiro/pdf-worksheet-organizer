from __future__ import annotations

import io
import typing as t
import contextlib

import pikepdf
import fitz as pymupdf
from PIL import ImageDraw, ImageFont

from pdf_worksheet_organizer.datatypes import (
    PdfFile,
    PdfFont,
    PdfNumberedFile,
    PdfNumberedWord,
    PdfNumberedImage,
    PdfNumberedPage,
)
from pdf_worksheet_organizer.parsing import fonts_pil_font


QUESTION_NUMBER_FORMAT = "{0})"


def renumber_pdf(
    pike_pdf: pikepdf.Pdf,
    mu_pdf: pymupdf.Document,
    pdf_file: PdfFile,
    numbered_pdf_file: PdfNumberedFile,
    fonts: list[PdfFont],
) -> pymupdf.Document:
    question_number = 1
    page_count = len(pdf_file.pages)

    new_pike_pdf = pike_pdf
    new_mu_pdf = mu_pdf
    last_type: t.Type[PdfNumberedWord] | t.Type[PdfNumberedImage]

    for page_num in range(page_count):
        numbered_pdf_page = numbered_pdf_file.pages[page_num]

        for element in numbered_pdf_page.elements:
            if isinstance(element, PdfNumberedWord):
                mu_page: pymupdf.Page = new_mu_pdf.load_page(page_num)
                renumber_text_element(question_number, fonts, mu_page, element)
                last_type = PdfNumberedWord
            else:  # if isinstance(element, PdfNumberedImage):
                pike_page = new_pike_pdf.pages[page_num]
                renumber_image_element(question_number, fonts, pike_page, element)
                last_type = PdfNumberedImage

            new_pike_pdf, new_mu_pdf = merge_pdfs(new_pike_pdf, new_mu_pdf, last_type)
            question_number += 1

    return new_mu_pdf


def merge_pdfs(
    pike_pdf: pikepdf.Pdf, mu_pdf: pymupdf.Document, last_type: t.Type[PdfNumberedWord] | t.Type[PdfNumberedImage]
) -> tuple[pikepdf.Pdf, pymupdf.Document]:
    # sourcery skip: use-assigned-variable
    pdf_bytes_io = io.BytesIO()

    new_pike_pdf = pike_pdf
    new_mu_pdf = mu_pdf

    # pymupdf handles updating text
    if last_type is PdfNumberedWord:
        mu_pdf.save(pdf_bytes_io)
        new_pike_pdf = pikepdf.open(pdf_bytes_io)

    # pikepdf handles updating images
    if last_type is PdfNumberedImage:
        pike_pdf.save(pdf_bytes_io)
        new_mu_pdf = pymupdf.Document(stream=pdf_bytes_io)

    return new_pike_pdf, new_mu_pdf


def renumber_text_element(
    question_number: int,
    fonts: list[PdfFont],
    mu_page: pymupdf.Page,
    numbered_pdf_word: PdfNumberedWord,
) -> int:
    text_writer = pymupdf.TextWriter(mu_page.rect)

    font = parse_font_from_fonts(numbered_pdf_word.font, fonts)

    match = numbered_pdf_word.match
    question_number_text = QUESTION_NUMBER_FORMAT.format(question_number)
    text = match.string.replace(match.group(), question_number_text)

    mu_page.add_redact_annot(quad=numbered_pdf_word.bounding_box)
    mu_page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)  # type: ignore

    text_writer.append(text=text, font=font, fontsize=round(numbered_pdf_word.font_size), pos=numbered_pdf_word.origin)

    question_number += 1

    text_writer.write_text(mu_page)

    return question_number


def renumber_image_element(
    question_number: int,
    fonts: list[PdfFont],
    pike_page: pikepdf.Page,
    numbered_pdf_image: PdfNumberedImage,
) -> None:
    number_bbox = numbered_pdf_image.number_bounding_box
    number_bbox_as_tuple: tuple[float, float, float, float] = tuple(number_bbox)  # type: ignore

    pil_image = numbered_pdf_image.as_pil_image()
    # very top left pixel should be the proper background color in most scenarios
    # this can be changed to a different (more expensive) computation if need be.

    font_size = round((number_bbox.y1 - number_bbox.y0) * (3 / 2))
    pil_font = fonts_pil_font(fonts, font_size)

    xy: tuple[float, float] = tuple(number_bbox.top_left)  # type: ignore
    text = QUESTION_NUMBER_FORMAT.format(question_number)

    background_color = pil_image.getpixel((0, 0))

    draw = ImageDraw.Draw(pil_image)
    draw.rectangle(number_bbox_as_tuple, fill=background_color)
    draw.text(xy, text=text, font=pil_font, fill=(0, 0, 0))

    raw_image = pil_image.tobytes()

    image_id = numbered_pdf_image.id
    str_image_id = str(image_id)
    keys = [k for k in pike_page.images.keys() if str_image_id in k]

    if not keys:
        raise ValueError(f"Could not find image with id {numbered_pdf_image.id}")

    pike_page.images[keys[0]].write(raw_image)


def load_page(
    page_num: int,
    mu_pdf: pymupdf.Document,
    numbered_pdf_file: PdfNumberedFile,
) -> tuple[pymupdf.Page, PdfNumberedPage]:
    mu_page: pymupdf.Page = mu_pdf.load_page(page_num)
    numbered_pdf_page = numbered_pdf_file.pages[page_num]

    return (mu_page, numbered_pdf_page)


def parse_font_from_fonts(font_name: str, fonts: list[PdfFont]) -> pymupdf.Font | None:
    for font in fonts:
        if font_name in font.name:
            return font.as_pymupdf_font()
    return None


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
