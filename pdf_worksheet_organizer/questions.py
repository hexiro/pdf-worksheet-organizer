from __future__ import annotations

import re
import operator
import typing as t

import fitz as pymupdf


from pdf_worksheet_organizer import ocr
from pdf_worksheet_organizer.datatypes import PdfNumberedFile, PdfNumberedPage, PdfNumberedImage, PdfNumberedWord


if t.TYPE_CHECKING:
    from datatypes import PdfFile, PdfPage, PdfText, PdfImages

NUMBERED_QUESTION_TEXT_REGEX = re.compile(r"(?:^| )(\d+[.)])(?=\s|$)")


def parse_numbered_pdf(pdf_file: PdfFile) -> PdfNumberedFile:
    numbered_pages: list[PdfNumberedPage] = []

    for page in pdf_file.pages:
        numbered_page = parse_numbered_page(page)
        numbered_pages.append(numbered_page)

    numbered_file = PdfNumberedFile(pages=numbered_pages)
    return numbered_file


def parse_numbered_elements(
    pdf_numbered_text: list[PdfNumberedWord], pdf_numbered_images: list[PdfNumberedImage]
) -> list[PdfNumberedWord | PdfNumberedImage]:  # sourcery skip: merge-list-extend
    # setting the list directly (as a copy) freaks out pylance for some reason
    pdf_numbered_els: list[PdfNumberedWord | PdfNumberedImage] = []
    pdf_numbered_els.extend(pdf_numbered_text)

    text_top_values: set[float] = {word.bounding_box.y0 for word in pdf_numbered_text}

    for image in pdf_numbered_images:
        image_top = image.bounding_box.y0

        diffs = (abs(image_top - text_top) for text_top in text_top_values)

        if all(diff > 25 for diff in diffs):
            pdf_numbered_els.append(image)
            continue

    return pdf_numbered_els


def parse_numbered_page(page: PdfPage) -> PdfNumberedPage:
    pdf_numbered_text = filter_numbered_text(page.text)
    pdf_numbered_images = filter_numbered_images(page.images)

    pdf_numbered_els = parse_numbered_elements(pdf_numbered_text, pdf_numbered_images)
    sort_by_bounding_box_top(pdf_numbered_els)

    return PdfNumberedPage(elements=pdf_numbered_els)


def filter_numbered_text(text: PdfText) -> list[PdfNumberedWord]:
    matching_words: list[PdfNumberedWord] = []

    for word in text:
        match = NUMBERED_QUESTION_TEXT_REGEX.search(word.text)
        if not match:
            continue

        new_word = PdfNumberedWord(
            text=word.text,
            font=word.font,
            font_size=word.font_size,
            bounding_box=word.bounding_box,
            origin=word.origin,
            match=match,
        )

        matching_words.append(new_word)

    return matching_words


def filter_numbered_images(images: PdfImages) -> list[PdfNumberedImage]:
    matching_images: list[PdfNumberedImage] = []

    for image in images:
        image_data = ocr.image_to_text(image)

        # TODO: maybe add check to see if match is on left <25% of image
        # (because thats where the question number is usually located)

        for index, word in enumerate(image_data["text"]):
            word = word.strip()
            match = NUMBERED_QUESTION_TEXT_REGEX.search(word)
            if not match:
                continue
            left = image_data["left"][index]
            top = image_data["top"][index]
            right = image_data["width"][index] + left
            bottom = image_data["height"][index] + top

            number_bbox = pymupdf.Rect(left, top, right, bottom)
            new_image = PdfNumberedImage(
                id=image.id,
                stream=image.stream,
                bounding_box=image.bounding_box,
                word=word,
                number_bounding_box=number_bbox,
            )
            matching_images.append(new_image)

            # only 1 match per image
            break

    return matching_images


def sort_by_bounding_box_top(
    elements: list[PdfNumberedImage] | list[PdfNumberedWord] | list[PdfNumberedImage | PdfNumberedWord],
) -> None:
    key = operator.attrgetter("bounding_box.y0")
    elements.sort(key=key)
