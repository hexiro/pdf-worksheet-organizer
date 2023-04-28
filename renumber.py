import io
import typing as t

import rich
import pikepdf
import fitz as pymupdf

from datatypes import FontBuffers, PdfFile, PdfNumberedFile, PdfNumberedWord, PdfPage, PdfNumberedPage
from paths import OUT_DIR

QUESTION_NUMBER_FORMAT = "{0})"


def renumber_pdf(
    pike_pdf: pikepdf.Pdf,
    mu_pdf: pymupdf.Document,
    pdf_file: PdfFile,
    numbered_pdf_file: PdfNumberedFile,
) -> None:
    font_buffers = parse_font_buffers(pike_pdf)
    page_count = len(pdf_file.pages)

    question_number = 1
    for page_num in range(page_count):
        question_number = parse_page(
            page_num, question_number, font_buffers, pike_pdf, mu_pdf, pdf_file, numbered_pdf_file
        )

    mu_pdf.save(OUT_DIR / "replaced.pdf", garbage=3, deflate=True)


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


def parse_page(
    page_num: int,
    question_number: int,
    font_buffers: FontBuffers,
    pike_pdf: pikepdf.Pdf,
    mu_pdf: pymupdf.Document,
    pdf_file: PdfFile,
    numbered_pdf_file: PdfNumberedFile,
) -> int:
    pike_page, mu_page, pdf_page, numbered_pdf_page = load_page(
        page_num, pike_pdf, mu_pdf, pdf_file, numbered_pdf_file
    )

    question_number = renumber_text_elements(question_number, font_buffers, mu_page, numbered_pdf_page)
    rich.print(question_number)

    return question_number


def renumber_text_elements(
    question_number: int,
    font_buffers: FontBuffers,
    mu_page: pymupdf.Page,
    numbered_pdf_page: PdfNumberedPage,
) -> int:
    text_writer = pymupdf.TextWriter(mu_page.rect)

    for word in numbered_pdf_page.elements:
        if not isinstance(word, PdfNumberedWord):
            continue

        font = parse_font_from_font_buffer(word.font, font_buffers)
        text = QUESTION_NUMBER_FORMAT.format(question_number)

        mu_page.add_redact_annot(quad=word.bounding_box)
        mu_page._apply_redactions()

        text_writer.append(text=text, font=font, fontsize=round(word.font_size), pos=word.origin)

        question_number += 1

    text_writer.write_text(mu_page)

    return question_number


def load_page(
    page_num: int,
    pike_pdf: pikepdf.Pdf,
    mu_pdf: pymupdf.Document,
    pdf_file: PdfFile,
    numbered_pdf_file: PdfNumberedFile,
) -> tuple[pikepdf.Page, pymupdf.Page, PdfPage, PdfNumberedPage]:
    pike_page = pike_pdf.pages[page_num]
    mu_page: pymupdf.Page = mu_pdf.load_page(page_num)
    pdf_page = pdf_file.pages[page_num]
    numbered_pdf_page = numbered_pdf_file.pages[page_num]

    return (pike_page, mu_page, pdf_page, numbered_pdf_page)


def parse_font_from_font_buffer(font_name: str, font_buffers: FontBuffers) -> pymupdf.Font:
    font_buffer: io.BytesIO | None

    for font_buffer_name, font_buffer_option in font_buffers.items():
        if font_name in font_buffer_name:
            font_buffer = font_buffer_option
            break
    else:
        key = list(font_buffers.keys())[0]
        font_buffer = font_buffers[key]

    return pymupdf.Font(fontname=font_name, fontbuffer=font_buffer)
