from __future__ import annotations

import re

import typing as t

import rich

import ocr

if t.TYPE_CHECKING:
    from datatypes import PdfFile, PdfPage, PdfImage, PdfWord, PdfText, PdfImages

NUMBERED_QUESTION_TEXT_REGEX = re.compile(r"^(\d+)[.)]$")


def parse_numbered_questions(pdf_file: PdfFile) -> list[PdfWord | PdfImage]:
    numbered_questions: list[PdfWord | PdfImage] = []

    for page in pdf_file.pages:
        page_numbered_questions = parse_numbered_questions_from_page(page)
        numbered_questions.extend(page_numbered_questions)

    return numbered_questions


def parse_numbered_questions_from_page(page: PdfPage) -> list[PdfWord | PdfImage]:
    numbered_questions: list[PdfWord | PdfImage] = []

    numbered_questions.extend(find_numbered_questions_from_text(page.text))
    numbered_questions.extend(find_numbered_questions_from_images(page.images))

    return numbered_questions


def find_numbered_questions_from_text(text: PdfText) -> PdfText:
    matching_words: list[PdfWord] = []

    for word in text:
        word_text = word.word.strip()
        match = NUMBERED_QUESTION_TEXT_REGEX.search(word_text)
        if not match:
            continue
        matching_words.append(word)

    return matching_words


def find_numbered_questions_from_images(images: PdfImages) -> PdfImages:
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
