import sys
from pathlib import Path
from typing import Optional

import typer
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger, setup_logger, time_it

from ihexer import __version__
from ihexer.ihexer import IntelHexDiff, IntelHexParser, IntelHexPrinter

package_name = "ihexer"

app = typer.Typer(name=package_name, help="Intel HEX utils.", no_args_is_help=True)


@app.callback(invoke_without_command=True)
def version(
    version: bool = typer.Option(None, "--version", "-v", is_eager=True, help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"{package_name} {__version__}")
        raise typer.Exit()


@app.command()
@time_it("view")
def view(
    file: Path = typer.Option(help="Input hex/bin file."),  # noqa: B008
    dump_to: Optional[Path] = typer.Option(None, help="Output file to dump the hex content."),  # noqa: B008
    short_info: bool = typer.Option(True, help="Dump hex file short info before the content."),
) -> None:
    intel_hex = IntelHexParser(file).parse()
    print(IntelHexPrinter(intel_hex).to_string(short_info))
    if dump_to:
        dump_to.write_text(IntelHexPrinter(intel_hex).to_string(short_info))


@app.command()
@time_it("diff")
def diff(
    first: Path = typer.Option(help="First input hex/bin file."),  # noqa: B008
    second: Path = typer.Option(help="Second input hex/bin file."),  # noqa: B008
    out_file: Path = typer.Option(help="Output file to write the html diff report."),  # noqa: B008
) -> None:
    IntelHexDiff(first, second).generate(out_file)


@app.command()
@time_it("info")
def info(
    file: Path = typer.Option(help="Input hex/bin file."),  # noqa: B008
) -> None:
    intel_hex = IntelHexParser(file).parse()
    for line in IntelHexPrinter.stringify_short_info(intel_hex.segments):
        print(line)


@app.command()
@time_it("swap")
def swap(
    file: Path = typer.Option(help="Input hex/bin file."),  # noqa: B008
    out_file: Optional[Path] = typer.Option(None, help="Output file to write the swapped hex content."),  # noqa: B008
    word_size: int = typer.Option(4, help="Word size in bytes."),
) -> None:
    IntelHexParser(file, bytes_swap=True, word_size=word_size).parse().write_hex_file(out_file or file)


def main() -> int:
    try:
        setup_logger()
        app()
        return 0
    except UserNotificationException as e:
        logger.error(f"{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
