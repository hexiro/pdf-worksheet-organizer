import io
import fitz as pymupdf
import rich

from pdf_worksheet_organizer.datatypes import PdfFile, PdfNumberedFile, PdfPage, Padding

from PIL import ImageFont, Image, ImageDraw

from pdf_worksheet_organizer.exceptions import NoAvailablePositionException


def create_legend_image(numbers: list[int]) -> Image.Image:
    new_number_to_number = list(enumerate(numbers, start=1))

    gap = 4
    padding = 8
    font_size = 12
    heading_text = "Legend"
    heading_font_size = round(font_size * (5 / 4))
    font_path = "assets/JetBrainsMono-Bold.ttf"

    font = ImageFont.truetype(font=font_path, size=font_size)
    heading_font = ImageFont.truetype(font=font_path, size=heading_font_size)

    heading_bbox = heading_font.getbbox(heading_text)
    heading_height = heading_bbox[3] - heading_bbox[1]
    heading_width = heading_bbox[2] - heading_bbox[0]
    heading_padding_bottom = 8

    def format_text(new_number: int, number: int) -> str:
        return f"{new_number}: {number}"

    def format_new_number(new_number: int) -> str:
        return f"{new_number}: "

    def format_number(new_number: int, number: int) -> str:
        num_spaces = len(str(new_number)) + 2
        return f"{' ' * num_spaces}{number}"

    max_width = 0
    max_height = 0
    for new_number, number in new_number_to_number:
        bbox = font.getbbox(format_text(new_number, number))
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]

        if bbox_width > max_width:
            max_width = bbox_width
        if bbox_height > max_height:
            max_height = bbox_height

    width = max(max_width, heading_width) + (padding * 2)
    height = (
        (max_height * len(numbers))
        + (gap * (len(numbers) - 1))
        + heading_height
        + heading_padding_bottom
        + (padding * 2)
    )
    fix_default_offset = (-max_height // 2) + 1

    pil_image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(pil_image)

    grey_val = round(255 / 5)
    heading_padding_left = (width - heading_width) // 2

    grey = (grey_val, grey_val, grey_val)
    black = (0, 0, 0)

    line_y = heading_height - 1 + padding
    line_x = heading_padding_left

    draw.rectangle((0, 0, width - 1, height - 1), outline=black, width=2)
    draw.line(
        xy=((line_x, line_y), (line_x + heading_width, line_y)),
        fill=grey,
        width=2,
    )

    draw.text(
        (heading_padding_left, fix_default_offset + padding),
        text=heading_text,
        font=heading_font,
        fill=black,
        spacing=0,
    )

    for new_number, number in new_number_to_number:
        x = padding
        y = (
            fix_default_offset
            + heading_height
            + heading_padding_bottom
            + padding
            + ((new_number - 1) * (max_height + gap))
        )

        draw.text((x, y), format_new_number(new_number), font=font, fill=black, spacing=0)
        draw.text((x, y), format_number(new_number, number), font=font, fill=grey, spacing=0)

    return pil_image


def add_legend(
    mu_pdf: pymupdf.Document,
    pdf_file: PdfFile,
    numbered_pdf_file: PdfNumberedFile,
) -> pymupdf.Document:
    numbers: list[int] = []
    for page in numbered_pdf_file.pages:
        numbers.extend(el.number for el in page.elements)

    legend_image = create_legend_image(numbers)

    mu_page: pymupdf.Page = mu_pdf.load_page(0)
    page = pdf_file.pages[0]

    position = find_position(mu_pdf[0], page, legend_image.size)

    legend_image_bytes_io = io.BytesIO()
    legend_image.save(legend_image_bytes_io, format="png")

    mu_page.insert_image(position, stream=legend_image_bytes_io.getvalue(), overlay=True)  # type: ignore

    return mu_pdf


def find_position(
    mu_page: pymupdf.Page,
    page: PdfPage,
    size: tuple[int, int],
) -> pymupdf.Rect:  # sourcery skip: set-comprehension
    image_width, image_height = size

    page_elements_bboxes: set[pymupdf.Rect] = set()

    for first_index, first_el in enumerate(page.elements):
        first_el_bbox = first_el.bounding_box
        is_inside = False

        for second_index, second_el in enumerate(page.elements):
            if first_index == second_index:
                continue
            if first_el_bbox in second_el.bounding_box:
                is_inside = True

        if not is_inside:
            expanded_bbox = expand_rect(first_el_bbox, 5)
            page_elements_bboxes.add(expanded_bbox)

    page_rect: pymupdf.Rect = mu_page.rect

    left_most_val = page_rect.x1
    top_most_val = page_rect.y1
    right_most_val = page_rect.x0
    bottom_most_val = page_rect.y0

    for element in page.elements:
        bbox = element.bounding_box
        if bbox.x0 < left_most_val:
            left_most_val = bbox.x0
        if bbox.y0 < top_most_val:
            top_most_val = bbox.y0
        if bbox.x1 > right_most_val:
            right_most_val = bbox.x1
        if bbox.y1 > bottom_most_val:
            bottom_most_val = bbox.y1

    left_most_val = round(left_most_val)
    top_most_val = round(top_most_val)
    right_most_val = round(right_most_val)
    bottom_most_val = round(bottom_most_val)

    x_vals = range(left_most_val, right_most_val)
    y_vals = range(top_most_val, bottom_most_val)

    rightmost_x = right_most_val - image_width
    bottommost_y = bottom_most_val - image_height

    possible_positions: tuple[tuple[int, int], ...] = (
        *((left_most_val, y) for y in y_vals),
        *((rightmost_x, y) for y in y_vals),
        *((x, top_most_val) for x in x_vals),
        *((x, bottommost_y) for x in x_vals),
    )

    for x, y in possible_positions:
        rect = pymupdf.Rect(x, y, x + image_width, y + image_height)
        if any(rect.intersects(el) for el in page_elements_bboxes):
            continue

        return rect

    raise NoAvailablePositionException("legend")


def expand_rect(rect: pymupdf.Rect, amount: int) -> pymupdf.Rect:
    return pymupdf.Rect(
        rect.x0 - amount,
        rect.y0 - amount,
        rect.x1 + amount,
        rect.y1 + amount,
    )


def shrink_rect(rect: pymupdf.Rect, offset_x: int, offset_y: int) -> pymupdf.Rect:
    return pymupdf.Rect(
        rect.x0 + offset_x,
        rect.y0 + offset_y,
        rect.x1 - offset_x,
        rect.y1 - offset_y,
    )
