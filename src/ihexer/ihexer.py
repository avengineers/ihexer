import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import List

from intelhex import IntelHex as _IntelHex
from py_app_dev.core.exceptions import UserNotificationException


@dataclass
class IntelHexSegment:
    start: int
    end: int
    data: bytes

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def __post_init__(self) -> None:
        """Make sure the segment can have a size."""
        if self.end < self.start:
            raise ValueError(f"Segments length has negative size: end {self.end} < start {self.start}.")

    def __str__(self) -> str:
        """Only print the address range."""
        return f"{hex(self.start)}-{hex(self.end)}: {self.length} bytes"


@dataclass
class IntelHex:
    start_address: int
    end_address: int
    segments: List[IntelHexSegment]

    def get_content(self) -> str:
        """Return the hex content of all segments as a single long string."""
        hex_content = []
        for segment in self.segments:
            hex_content.append(segment.data.hex().upper())
        return "".join(hex_content)

    def __str__(self) -> str:
        """Return the content when the object is printed."""
        return self.get_content()

    def write_hex_file(self, output_file: Path) -> None:
        """Write the IntelHex content back to a hex file."""
        # Create a new _IntelHex object to store the data
        intel_hex = _IntelHex()

        # For each segment, add its data to the _IntelHex object
        for segment in self.segments:
            intel_hex.puts(segment.start, segment.data)

        # Write the data to the specified file
        intel_hex.write_hex_file(output_file.as_posix())


class IntelHexParser:
    def __init__(self, file: Path, bytes_swap: bool = False, word_size: int = 4) -> None:
        self.file = file
        self.bytes_swap = bytes_swap
        self.word_size = word_size

    def parse(self) -> IntelHex:
        segments = self._read_segments(self._parse_content())
        return IntelHex(
            min([segment.start for segment in segments]),
            max([segment.end for segment in segments]),
            segments,
        )

    def _parse_content(self) -> _IntelHex:
        _content = _IntelHex()
        format = self.file.suffix.lower().replace(".", "")
        try:
            _content.loadfile(self.file.as_posix(), format)
        except ValueError as e:
            raise UserNotificationException(f"Could not load '{self.file}'. Unsupported format {format}") from e
        return _content

    def _read_segments(self, content: _IntelHex) -> List[IntelHexSegment]:
        segments: List[IntelHexSegment] = []
        _segments = content.segments()
        if _segments:
            for segment_addresses_list in _segments:
                start_address = segment_addresses_list[0]
                # For some reason IntelHex sets the end address to the next available address. Bug?
                end_address = segment_addresses_list[1] - 1
                data: bytes = content.gets(start_address, end_address - start_address + 1)
                if self.bytes_swap:
                    data = self.swap_bytes(data, self.word_size)
                segments.append(
                    IntelHexSegment(
                        start_address,
                        end_address,
                        data,
                    )
                )
        return segments

    @staticmethod
    def swap_bytes(data: bytes, word_size: int) -> bytes:
        if len(data) % word_size != 0:
            raise UserNotificationException(f"Data length {len(data)} is not a multiple of word size {word_size}.")
        swapped_data = bytearray()
        for i in range(0, len(data), word_size):
            swapped_data.extend(reversed(data[i : i + word_size]))
        return bytes(swapped_data)


class IntelHexPrinter:
    def __init__(self, content: IntelHex) -> None:
        self.content = content

    @staticmethod
    def stringify_segment(segment: IntelHexSegment) -> List[str]:
        output_lines = []
        # Calculate the alignment offset from the nearest lower multiple of 16
        alignment_offset = segment.start % 16

        # Adjust the start address to be aligned to 16 bytes
        aligned_start_address = segment.start - alignment_offset

        # Calculate the number of lines, ensuring at least one line
        # Include the offset in the calculation for total data length
        num_lines = (len(segment.data) + alignment_offset + 15) // 16 if segment.data else 1

        for i in range(num_lines):
            start_idx = i * 16 - alignment_offset
            end_idx = start_idx + 16
            current_data_chunk = segment.data[max(0, start_idx) : end_idx]

            address_str = f"{aligned_start_address + i*16:08X}"

            # Prepare the data bytes, filling missing bytes with '--' at the beginning due to alignment
            data_strs = ["--"] * max(0, -start_idx)  # Fill with '--' if start_idx is negative
            data_strs += [f"{byte:02X}" for byte in current_data_chunk]
            missing_bytes = 16 - len(data_strs)
            data_strs.extend(["--"] * missing_bytes)

            data_str = " ".join(data_strs)
            segment_str = f"{address_str}: {data_str}"
            output_lines.append(segment_str)
        return output_lines

    @staticmethod
    def stringify_segments(segments: List[IntelHexSegment]) -> List[str]:
        output_lines = []
        for segment in segments:
            output_lines.extend(IntelHexPrinter.stringify_segment(segment))
        return output_lines

    @staticmethod
    def stringify_short_info(segments: List[IntelHexSegment]) -> List[str]:
        delimiter = "-" * 57
        output_lines = [delimiter, "SEGMENTS:"]
        for segment in segments:
            output_lines.append(str(segment))
        output_lines.append(delimiter)
        return output_lines

    def to_string(self, with_short_info: bool = True) -> str:
        content = []
        if with_short_info:
            content.extend(IntelHexPrinter.stringify_short_info(self.content.segments))
        content.extend(IntelHexPrinter.stringify_segments(self.content.segments))
        return "\n".join(content)


class IntelHexDiff:
    def __init__(self, first: Path, second: Path) -> None:
        self.first_file = first
        self.second_file = second

    def generate_html(self) -> str:
        first_list = IntelHexPrinter.stringify_segments(IntelHexParser(self.first_file).parse().segments)
        second_list = IntelHexPrinter.stringify_segments(IntelHexParser(self.second_file).parse().segments)

        html_diff = difflib.HtmlDiff()

        return html_diff.make_file(
            first_list,
            second_list,
            fromdesc=f"{self.first_file}",
            todesc=f"{self.second_file}",
            context=True,
            numlines=5,
        )

    def generate(self, out_file: Path) -> None:
        out_file.write_text(self.generate_html())
