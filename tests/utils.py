from pathlib import Path

this_dir = Path(__file__).parent


def get_tests_data_file(file: str) -> Path:
    return this_dir / "data" / file


def write_file(file: Path, content: str) -> Path:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    return file
