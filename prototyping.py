import pathlib
import pikepdf
import fitz as pymupdf

from PIL import Image, ImageDraw

from paths import OUT_DIR, PDF_PATH


def prove_editing_pdf_images_works(
    page: pikepdf.Page,
    image_name_to_stream: dict[str, pikepdf.Stream],
) -> pikepdf.Page:
    for image_key, image in image_name_to_stream.items():
        pdf_image = pikepdf.PdfImage(image)

        pil_image = pdf_image.as_pil_image()

        width, height = pil_image.size

        # Calculate the center point of the image
        center_x = width // 2
        center_y = height // 2

        # Create a new ImageDraw object
        draw = ImageDraw.Draw(pil_image)

        # Draw a red circle with a diameter of 16 pixels in the center
        circle_radius = 8
        circle_coords = (
            center_x - circle_radius,
            center_y - circle_radius,
            center_x + circle_radius,
            center_y + circle_radius,
        )
        draw.ellipse(circle_coords, fill="red")

        raw_image = pil_image.tobytes()

        page.images[image_key].write(raw_image)

    return page


def draw_outlines_around_images(page: pymupdf.Page, image_name_to_dimensions: dict[str, pymupdf.IRect]) -> None:
    def image_mode(pix: pymupdf.Pixmap) -> str:
        """
        Image mode function from Pixmap.pil_save function
        """
        colorspace = pix.colorspace
        no_alpha = pix.alpha == 0

        if colorspace is None:
            return "L"
        elif colorspace.n == 1:
            return r"L" if no_alpha else "LA"
        elif colorspace.n == 3:
            return "RGB" if no_alpha else "RGBA"
        else:
            return "CMYK"

    pix: pymupdf.Pixmap = page.get_pixmap()  # type: ignore
    pix.pil_save
    img = Image.frombytes(image_mode(pix), (pix.width, pix.height), pix.samples)

    for bounding_box in image_name_to_dimensions.values():
        draw = ImageDraw.Draw(img)
        four_corners: tuple[float, float, float, float] = tuple(bounding_box)  # type: ignore
        draw.rectangle(four_corners, outline="red")

    img.show()


def extract_images(page: pikepdf.Page) -> None:
    for image_name, image in page.images.items():
        pdf_image = pikepdf.PdfImage(image)
        pil_image = pdf_image.as_pil_image()

        image_name = image_name.removeprefix("/")

        pil_image.save(OUT_DIR / f"{image_name}.png")


if __name__ == "__main__":
    pdf = pikepdf.open(PDF_PATH)
    page_one = pdf.pages[0]

    extract_images(page_one)
