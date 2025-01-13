from pathlib import Path

from ihex.ihex import IntelHexParser, IntelHexPrinter, IntelHexSegment
from tests.utils import get_tests_data_file


def test_intel_hex_parser(tmp_path: Path) -> None:
    # original input to be parsed
    hex_file = get_tests_data_file("sixteen_bytes.hex")

    # IUT: parse once with default settings
    intel_hex = IntelHexParser(hex_file).parse()

    # Test the parsed content
    assert intel_hex
    assert intel_hex.start_address == 0x1000
    assert intel_hex.end_address == 0x100F
    assert len(intel_hex.segments) == 1
    assert intel_hex.segments[0].start == 0x1000
    assert intel_hex.segments[0].end == 0x100F
    assert intel_hex.segments[0].data == bytes.fromhex("FF81DF09" "ED869E9E" "F557AE21" "93518974")

    # Write the parsed content to a new file
    intel_hex.write_hex_file(tmp_path / "sixteen_bytes.hex")

    # New file shall be identical to the original file
    assert (tmp_path / "sixteen_bytes.hex").read_text() == hex_file.read_text()

    # Create a swapped version of the original file
    swapped_intel_hex = IntelHexParser(hex_file, bytes_swap=True).parse()
    assert swapped_intel_hex.segments[0].data == bytes.fromhex("09DF81FF" "9E9E86ED" "21AE57F5" "74895193")
    swapped_intel_hex.write_hex_file(tmp_path / "sixteen_bytes_swapped.hex")
    assert (tmp_path / "sixteen_bytes_swapped.hex").read_text() == ":1010000009DF81FF9E9E86ED21AE57F574895193CD\n:00000001FF\n"

    # Swap the swapped file back to original
    swapped_back_intel_hex = IntelHexParser(tmp_path / "sixteen_bytes_swapped.hex", bytes_swap=True).parse()
    swapped_back_intel_hex.write_hex_file(tmp_path / "sixteen_bytes_swapped_back.hex")
    assert (tmp_path / "sixteen_bytes_swapped_back.hex").read_text() == hex_file.read_text()


def test_swap_bytes():
    assert IntelHexParser.swap_bytes(bytes.fromhex("01020304"), 2) == bytes.fromhex("02010403")
    assert IntelHexParser.swap_bytes(bytes.fromhex("01020304"), 4) == bytes.fromhex("04030201")
    assert IntelHexParser.swap_bytes(bytes.fromhex("010203040a0b0c0d"), 4) == bytes.fromhex("040302010d0c0b0a")
    assert IntelHexParser.swap_bytes(IntelHexParser.swap_bytes(bytes.fromhex("01020304"), 4), 4) == bytes.fromhex("01020304")


def test_intel_hex_printer():
    content = IntelHexPrinter(IntelHexParser(get_tests_data_file("two_segments.hex")).parse()).to_string(with_short_info=False)
    assert (
        content
        == """\
00000010: A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4
00000020: A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4
00000080: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
00000090: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF"""
    )


def test_intel_hex_printer_with_short_info():
    content = IntelHexPrinter(IntelHexParser(get_tests_data_file("two_segments.hex")).parse()).to_string(with_short_info=True)
    assert (
        content
        == """\
---------------------------------------------------------
SEGMENTS:
0x10-0x2f: 32 bytes
0x80-0x9f: 32 bytes
---------------------------------------------------------
00000010: A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4
00000020: A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4
00000080: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
00000090: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF"""
    )


def test_intel_hex_printer_not_aligned():
    content = IntelHexPrinter(IntelHexParser(get_tests_data_file("not_aligned.hex")).parse()).to_string(with_short_info=False)
    assert (
        content
        == """\
00000010: -- -- -- -- -- A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4
00000020: A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4
00000080: FF FF FF FF FF FF FF FF FF FF -- -- -- -- -- --
00000090: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF"""
    )


def test_segment_to_string_normal_segment() -> None:
    segment = IntelHexSegment(start=0x10, end=0x1F, data=bytes(range(16)))
    expected_output = ["00000010: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F"]
    assert IntelHexPrinter.stringify_segment(segment) == expected_output


def test_segment_to_string_short_segment() -> None:
    segment = IntelHexSegment(start=0x20, end=0x27, data=bytes(range(8)))
    expected_output = ["00000020: 00 01 02 03 04 05 06 07 -- -- -- -- -- -- -- --"]
    assert IntelHexPrinter.stringify_segment(segment) == expected_output


def test_segment_to_string_long_segment() -> None:
    segment = IntelHexSegment(start=0x30, end=0x4F, data=bytes(range(32)))
    expected_output = [
        "00000030: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F",
        "00000040: 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F",
    ]
    assert IntelHexPrinter.stringify_segment(segment) == expected_output


def test_segment_to_string_no_data_segment() -> None:
    segment = IntelHexSegment(start=0x60, end=0x60, data=b"")
    expected_output = ["00000060: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --"]
    assert IntelHexPrinter.stringify_segment(segment) == expected_output


def test_intel_hex_get_content() -> None:
    intel_hex = IntelHexParser(get_tests_data_file("two_segments.hex")).parse()
    expected_content = "A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4A4FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    assert intel_hex.get_content() == expected_content
    assert str(intel_hex) == expected_content
