from __future__ import annotations

import re
import operator
import typing as t

from datatypes import PdfNumberedFile, PdfNumberedPage

import ocr

if t.TYPE_CHECKING:
    from datatypes import PdfFile, PdfPage, PdfImage, PdfWord, PdfText, PdfImages

NUMBERED_QUESTION_TEXT_REGEX = re.compile(r"^(\d+)[.)]$")


def parse_numbered_pdf(pdf_file: PdfFile) -> PdfNumberedFile:
    numbered_pages: list[PdfNumberedPage] = []

    for page in pdf_file.pages:
        numbered_page = parse_numbered_page(page)
        numbered_pages.append(numbered_page)

    numbered_file = PdfNumberedFile(pages=numbered_pages)
    return numbered_file


def parse_numbered_page(page: PdfPage) -> PdfNumberedPage:
    pdf_numbered_text = filter_numbered_text(page.text)
    pdf_numbered_images = filter_numbered_images(page.images)

    sort_by_bounding_box_top(pdf_numbered_text)
    sort_by_bounding_box_top(pdf_numbered_images)

    return PdfNumberedPage(text=pdf_numbered_text, images=pdf_numbered_images)


def filter_numbered_text(text: PdfText) -> PdfText:
    matching_words: list[PdfWord] = []

    for word in text:
        word_text = word.word.strip()
        match = NUMBERED_QUESTION_TEXT_REGEX.search(word_text)
        if not match:
            continue
        matching_words.append(word)

    return matching_words


def filter_numbered_images(images: PdfImages) -> PdfImages:
    matching_images: list[PdfImage] = []

    for image in images:
        image_data = ocr.image_to_text(image)

        # TODO: maybe add check to see if match is on left <25% of image
        # (because thats where the question number is usually located)

        for word in image_data["text"]:
            word = word.strip()
            match = NUMBERED_QUESTION_TEXT_REGEX.search(word)
            if not match:
                continue
            matching_images.append(image)
            break

    return matching_images


def sort_by_bounding_box_top(elements: list[PdfImage] | list[PdfWord] | list[PdfImage | PdfWord]) -> None:
    key = operator.attrgetter("bounding_box.y0")
    elements.sort(key=key)
