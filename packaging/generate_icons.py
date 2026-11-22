"""Generate multi-resolution PNG and Windows ICO icons matching the Personal AI Workspace brand mark."""

from pathlib import Path
import struct

import fitz  # PyMuPDF renders crisp vector graphics to PNG

SVG_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect x="12" y="12" width="232" height="232" rx="56" fill="#1C1B19" stroke="#D97757" stroke-width="10"/>
  <path d="M128 54L188 128L128 202L68 128L128 54Z" fill="none" stroke="#D97757" stroke-width="14" stroke-linejoin="round"/>
  <circle cx="128" cy="128" r="18" fill="#D97757"/>
</svg>
"""


def write_ico(png_frames: list[tuple[int, bytes]], output_path: Path) -> None:
    """Pack PNG-compressed frames into a standard multi-size Windows .ico file."""
    count = len(png_frames)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = bytearray()
    blobs = bytearray()

    for size, data in png_frames:
        dim = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset
        )
        blobs += data
        offset += len(data)

    output_path.write_bytes(header + entries + blobs)


def main() -> None:
    icons_dir = Path(__file__).resolve().parent / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    svg_path = icons_dir / "app_icon.svg"
    svg_path.write_text(SVG_ICON, encoding="utf-8")

    doc = fitz.open(stream=SVG_ICON.encode("utf-8"), filetype="svg")
    page = doc[0]

    frames: list[tuple[int, bytes]] = []
    for size in (16, 32, 48, 64, 128, 256):
        scale = size / 256.0
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=True)
        png_bytes = pix.tobytes("png")
        frames.append((size, png_bytes))
        if size == 256:
            (icons_dir / "app_icon.png").write_bytes(png_bytes)

    doc.close()
    write_ico(frames, icons_dir / "app_icon.ico")
    print(f"Generated {icons_dir / 'app_icon.ico'} and {icons_dir / 'app_icon.png'}")


if __name__ == "__main__":
    main()
