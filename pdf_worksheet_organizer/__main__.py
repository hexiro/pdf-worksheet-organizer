import pathlib

import rich.traceback
import rich_click as click

from pdf_worksheet_organizer import organizer


@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
def organize(input: str, output: str) -> None:
    input_path = pathlib.Path(input).resolve()
    output_path = pathlib.Path(output).resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path == output_path:
        raise FileExistsError(f"Input and output paths are the same: {input_path}")

    if output_path.is_dir():
        new_name = f"{input_path.stem}-replaced.pdf".replace(" ", "-")
        output_path = output_path / new_name

    new_pdf, questions_count = organizer.reorganize(input_path)
    new_pdf.save(output_path, garbage=3, deflate=True)

    relative_output_path = output_path.relative_to(pathlib.Path.cwd())

    rich.print(
        f"[bold][green]Saving renumbered PDF to [white]'{relative_output_path}'[/white] [white]([green]{questions_count} questions[/green])[/white][/bold][/green]"
    )


if __name__ == "__main__":
    rich.traceback.install()
    organize()
