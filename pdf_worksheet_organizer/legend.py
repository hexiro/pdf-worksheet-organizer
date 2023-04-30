import io
import fitz as pymupdf
import rich

from pdf_worksheet_organizer.datatypes import PdfFile, PdfNumberedFile, PdfPage

from PIL import ImageFont, Image, ImageDraw


def create_legend_image(numbers: list[int]) -> Image.Image:
    new_number_to_number = list(enumerate(numbers, start=1))

    padding = (16, 12)
    padding_x, padding_y = padding
    gap = 4
    font_size = 40

    font = ImageFont.truetype(font="assets/JetBrainsMono-Bold.ttf", size=font_size)

    def format_text(new_number: int, number: int) -> str:
        return f"{new_number}: {number}"

    max_width = 0
    max_height = 0
    for new_number, number in new_number_to_number:
        bbox = font.getbbox(format_text(new_number, number))
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if width > max_width:
            max_width = width
        if height > max_height:
            max_height = height

    width = max_width + padding_x * 2
    height = (max_height * len(numbers)) + (gap * (len(numbers) - 1)) + padding_y * 2
    fix_default_offset = (-max_height // 2) + 1

    pil_image = Image.new("RGBA", (width, height), (0, 0, 0, int(255 * 0.2)))

    draw = ImageDraw.Draw(pil_image)

    for new_number, number in new_number_to_number:
        x = padding_x
        y = fix_default_offset + padding_y + (new_number - 1) * (max_height + gap)

        draw.text((x, y), format_text(new_number, number), font=font, fill=(255, 255, 255, 255), spacing=0)

    # pil_image.show()
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

    for text in page.text:
        page_elements_bboxes.add(text.bounding_box)
    for image in page.images:
        page_elements_bboxes.add(image.bounding_box)

    padding_x = 20
    padding_y = 30
    page_rect: pymupdf.Rect = shrink_rect(mu_page.rect, padding_x, padding_y)
    rich.print(f"{page_rect=}")

    for x_offset in range(padding_x, int(page_rect.width) - padding_x):
        for y_offset in range(padding_y, int(page_rect.height) - padding_y):
            image_rect = pymupdf.Rect(
                x_offset,
                image_height,
                x_offset + image_width,
                y_offset + image_height,
            )

            if any(image_rect.intersects(el) for el in page_elements_bboxes):
                continue

            return image_rect

    raise Exception("Could not find a position for the legend")


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
