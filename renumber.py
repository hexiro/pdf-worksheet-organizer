import io
import os
import typing as t

import rich
import pikepdf
import fitz as pymupdf

from datatypes import (
    FontBuffers,
    PdfFile,
    PdfNumberedFile,
    PdfNumberedWord,
    PdfNumberedImage,
    PdfPage,
    PdfNumberedPage,
)
from paths import OUT_DIR

from PIL import ImageDraw, ImageFont, Image

QUESTION_NUMBER_FORMAT = "{0})"


def renumber_pdf(
    pike_pdf: pikepdf.Pdf,
    mu_pdf: pymupdf.Document,
    pdf_file: PdfFile,
    numbered_pdf_file: PdfNumberedFile,
) -> None:
    font_buffers = parse_font_buffers(pike_pdf)
    font_buffer = first_font_buffer(font_buffers)

    question_number = 1
    page_count = len(pdf_file.pages)

    new_pike_pdf = pike_pdf
    new_mu_pdf = mu_pdf
    last_type: t.Type[PdfNumberedWord] | t.Type[PdfNumberedImage]

    for page_num in range(page_count):
        numbered_pdf_page = numbered_pdf_file.pages[page_num]

        for element in numbered_pdf_page.elements:
            # rich.print(question_number)
            # rich.print(dict(new_pike_pdf.pages[0].images))

            if isinstance(element, PdfNumberedWord):
                mu_page: pymupdf.Page = new_mu_pdf.load_page(page_num)
                renumber_text_element(question_number, font_buffers, mu_page, element)
                last_type = PdfNumberedWord
            else:  # if isinstance(element, PdfNumberedImage):
                pike_page = new_pike_pdf.pages[page_num]
                renumber_image_element(question_number, font_buffer, pike_page, element)
                last_type = PdfNumberedImage

            new_pike_pdf, new_mu_pdf = merge_pdfs(new_pike_pdf, new_mu_pdf, last_type)
            question_number += 1

    new_mu_pdf.save(OUT_DIR / "out.pdf")
    # new_pike_pdf.save(OUT_DIR / "replaced2.pdf")


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


def parse_font_buffers(pike_pdf: pikepdf.Pdf) -> FontBuffers:
    font_buffers: FontBuffers = {}
    fonts_values: list[pikepdf.Dictionary] = []

    for page in pike_pdf.pages:
        fonts = page.resources["/Font"]
        values: t.Generator[pikepdf.Dictionary, None, None] = (v for _, v in fonts.items())  # type: ignore
        fonts_values.extend(values)

    for font in fonts_values:
        descriptor = font["/FontDescriptor"]
        font_name = str(descriptor["/FontName"])

        if font_name in font_buffers:
            continue

        font_buffer: io.BytesIO | None
        try:
            font_stream: pikepdf.Stream = descriptor["/FontFile2"]  # type: ignore
        except KeyError:
            # font doesn't need to be loaded, just referenced by name.
            # (must already be in system, on pdf or something im not exactly sure what the params are for this)
            font_buffer = None
        else:
            font_buffer = io.BytesIO(font_stream.get_stream_buffer())  # type: ignore

        font_buffers[font_name] = font_buffer

    return font_buffers


def renumber_text_element(
    question_number: int,
    font_buffers: FontBuffers,
    mu_page: pymupdf.Page,
    numbered_pdf_word: PdfNumberedWord,
) -> int:
    text_writer = pymupdf.TextWriter(mu_page.rect)

    font = parse_font_from_font_buffer(numbered_pdf_word.font, font_buffers)
    text = QUESTION_NUMBER_FORMAT.format(question_number)

    mu_page.add_redact_annot(quad=numbered_pdf_word.bounding_box)
    # calling this function standardizes the images to be in the format "/Im1", "/Im2", etc.
    mu_page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)  # type: ignore

    text_writer.append(text=text, font=font, fontsize=round(numbered_pdf_word.font_size), pos=numbered_pdf_word.origin)

    question_number += 1

    text_writer.write_text(mu_page)

    return question_number


def renumber_image_element(
    question_number: int,
    font_buffer: io.BytesIO | None,
    pike_page: pikepdf.Page,
    numbered_pdf_image: PdfNumberedImage,
) -> None:
    number_bbox = numbered_pdf_image.number_bounding_box
    number_bbox_as_tuple: tuple[float, float, float, float] = tuple(number_bbox)  # type: ignore

    pil_image = numbered_pdf_image.as_pil_image()
    # very top left pixel should be the proper background color in most scenarios
    # this can be changed to a different (more expensive) computation if need be.
    background_color = pil_image.getpixel((0, 0))

    draw = ImageDraw.Draw(pil_image)
    draw.rectangle(number_bbox_as_tuple, fill=background_color)

    font_size = round((number_bbox.y1 - number_bbox.y0) * (3 / 2))
    # TODO: maybe include encoding= param here which can be gotten from font data w/ pikepdf
    font = ImageFont.truetype(font=font_buffer, size=font_size)
    xy: tuple[float, float] = tuple(number_bbox.top_left)  # type: ignore
    text = QUESTION_NUMBER_FORMAT.format(question_number)

    draw.text(xy, text=text, font=font, fill=(0, 0, 0))

    raw_image = pil_image.tobytes()

    possible_keys = (f"/Image{numbered_pdf_image.id}", f"/Im{numbered_pdf_image.id}")

    for key in possible_keys:
        if key in pike_page.images:
            break
    else:
        raise ValueError(f"Could not find image with id {numbered_pdf_image.id}")

    pike_page.images[key].write(raw_image)


def load_page(
    page_num: int,
    mu_pdf: pymupdf.Document,
    numbered_pdf_file: PdfNumberedFile,
) -> tuple[pymupdf.Page, PdfNumberedPage]:
    mu_page: pymupdf.Page = mu_pdf.load_page(page_num)
    numbered_pdf_page = numbered_pdf_file.pages[page_num]

    return (mu_page, numbered_pdf_page)


def first_font_buffer(font_buffers: FontBuffers) -> io.BytesIO | None:
    for font_buffer in font_buffers.values():
        if font_buffer:
            return font_buffer
    return None


def parse_font_from_font_buffer(font_name: str, font_buffers: FontBuffers) -> pymupdf.Font:
    font_buffer: io.BytesIO | None

    for font_buffer_name, font_buffer_option in font_buffers.items():
        if font_name in font_buffer_name:
            font_buffer = font_buffer_option
            break
    else:
        font_buffer = first_font_buffer(font_buffers)

    return pymupdf.Font(fontname=font_name, fontbuffer=font_buffer)
