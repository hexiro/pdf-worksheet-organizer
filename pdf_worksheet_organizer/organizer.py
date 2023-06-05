import io
import pathlib

import pikepdf
import fitz as pymupdf

from pdf_worksheet_organizer.datatypes import (
    MuTextDict,
    PdfFont,
    PdfImage,
    PdfPage,
    PdfFile,
    PdfWord,
    PdfText,
    MuImage,
)
from pdf_worksheet_organizer import questions, renumber, legend


def image_name_as_int(image_name: str) -> int:
    image_name = image_name.removeprefix("/")
    image_name = image_name.removeprefix("Im")
    image_name = image_name.removeprefix("age")
    if not image_name.isdigit():
        raise ValueError(f"Image name {image_name} is not a digit")
    return int(image_name)


def parse_pdf_text(mu_page: pymupdf.Page) -> PdfText:
    text_page: pymupdf.TextPage = mu_page.get_textpage()
    text_dict: MuTextDict = text_page.extractDICT()  # type: ignore

    pdf_text: PdfText = []

    for block in text_dict["blocks"]:
        for line in block["lines"]:
            for word in line["spans"]:
                text = word["text"].strip()
                # text is probably just a space that got stripped out
                # -- not important to functionality so just skip
                if not text:
                    continue
                font = word["font"]
                font_size = word["size"]
                bounding_box = pymupdf.Rect(*word["bbox"])
                origin = pymupdf.Point(*word["origin"])

                pdf_word = PdfWord(
                    text=text,
                    font=font,
                    font_size=font_size,
                    bounding_box=bounding_box,
                    origin=origin,
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

    for pike_image_id, mu_image in enumerate(mu_images, start=1):
        image_dimensions = mu_image["bbox"]
        image_stream = pike_images[pike_image_id]

        pdf_image = PdfImage(
            id=pike_image_id,
            stream=image_stream,
            bounding_box=pymupdf.Rect(image_dimensions),
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


def reorganize(pdf_path: pathlib.Path, add_legend: bool) -> tuple[pymupdf.Document, int]:
    pike_pdf, mu_pdf = standardize_pdf(pdf_path)

    pdf_file = parse_pdf(pike_pdf, mu_pdf)
    numbered_pdf_file = questions.parse_numbered_pdf(pdf_file)

    fonts = parse_pdf_fonts(mu_pdf)
    final_pdf = renumber.renumber_pdf(pike_pdf, mu_pdf, pdf_file, numbered_pdf_file, fonts)

    if add_legend:
        final_pdf = legend.add_legend(final_pdf, pdf_file, numbered_pdf_file)

    return final_pdf, numbered_pdf_file.questions_count


def standardize_pdf(pdf_path: pathlib.Path) -> tuple[pikepdf.Pdf, pymupdf.Document]:
    mu_pdf = pymupdf.Document(pdf_path)

    # the `apply_redactions` function has the (undocumented) side effect of
    # reordering all images from their original ids (which can be any number and in no specific order) 
    # to an ordered 1, 2, 3, etc.

    # this is a problem because each image's id is used to reference the image and is what allows us
    # to modify each image. If these id's are changed, we can no longer reliably know which image is which.

    # to avoid this, we allow this side effect to take place 
    # before we parse the pdfs so the ids will remain consistent

    mu_page: pymupdf.Page
    for mu_page in mu_pdf.pages():
        mu_page.add_redact_annot(quad=pymupdf.Rect(0, 0, 0, 0))
        mu_page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)  # type: ignore

    pdf_bytes_io = io.BytesIO()
    mu_pdf.save(pdf_bytes_io)

    pike_pdf = pikepdf.open(pdf_bytes_io)

    return pike_pdf, mu_pdf


def parse_pdf_fonts(mu_pdf: pymupdf.Document) -> list[PdfFont]:
    mu_page: pymupdf.Page = mu_pdf.load_page(0)

    # https://pymupdf.readthedocs.io/en/latest/document.html#Document.extract_font
    # xref (int) is the font object number (may be zero if the PDF uses one of the builtin fonts directly)
    # ext (str) font file extension (e.g. “ttf”, see Font File Extensions)
    # type (str) is the font type (like “Type1” or “TrueType” etc.)
    # basefont (str) is the base font name,
    # name (str) is the symbolic name, by which the font is referenced
    # encoding (str) the font’s character encoding if different from its built-in encoding (Adobe PDF References, p. 254):
    # referencer
    mu_fonts: list[tuple[int, str, str, str, str, str, int]] = mu_page.get_fonts(full=True)
    pdf_fonts: list[PdfFont] = []

    for mu_font in mu_fonts:
        xref = mu_font[0]
        # (basename, ext, type, content)
        mu_font_info: tuple[str, str, str, bytes] = mu_pdf.extract_font(xref=xref)
        raw_bytes = mu_font_info[3]

        # TODO: revisit this
        # the problem here stems from the fact that if a font doesn't have a buffer with it
        # then is it is annoying to work with
        # for example, 'Times New Roman' won't have a buffer and its
        # file is called 'times.ttf' so it's not super intuitive to find
        if not raw_bytes:
            continue

        name = mu_font[3]
        encoding = mu_font[5]
        buffer = io.BytesIO(raw_bytes)

        pdf_font = PdfFont(
            name=name,
            encoding=encoding,
            buffer=buffer,
        )

        pdf_fonts.append(pdf_font)

    return pdf_fonts
