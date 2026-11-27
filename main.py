"""Publish the validated, pre-rendered make.fun entry without transcoding."""

import hashlib
from pathlib import Path

MAX_BYTES = 1024 * 1024
FRAME_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def jpeg_dimensions(image: bytes) -> tuple[int, int]:
    if not image.startswith(b"\xff\xd8"):
        raise ValueError("missing JPEG signature")

    offset = 2
    while offset < len(image) and image[offset] == 0xFF:
        while offset < len(image) and image[offset] == 0xFF:
            offset += 1
        if offset + 3 > len(image):
            break
        marker = image[offset]
        if marker in (0x00, 0xDA, 0xD9):
            break
        length = int.from_bytes(image[offset + 1:offset + 3], "big")
        if length < 2 or offset + 1 + length > len(image):
            break
        if marker in FRAME_MARKERS and length >= 8:
            height = int.from_bytes(image[offset + 4:offset + 6], "big")
            width = int.from_bytes(image[offset + 6:offset + 8], "big")
            return width, height
        offset += length + 1
    raise ValueError("missing or truncated JPEG frame header")


def main() -> None:
    source = Path(__file__).resolve().with_name("entry.jpg")
    with source.open("rb") as file:
        image = file.read(MAX_BYTES + 1)
    if not image:
        raise SystemExit("entry.jpg is empty")
    if len(image) > MAX_BYTES:
        raise SystemExit("entry.jpg exceeds 1 MiB")
    try:
        if jpeg_dimensions(image) != (1024, 1024):
            raise ValueError("expected a 1024 × 1024 frame")
    except ValueError as error:
        raise SystemExit(f"entry.jpg: {error}") from error

    destination = Path("/output/entry.png")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(image)
    except OSError:
        destination = Path("output/entry.png")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(image)

    digest = hashlib.sha256(image).hexdigest()
    try:
        written = destination.read_bytes()
    except OSError as error:
        raise SystemExit(f"{destination}: could not read back the published entry: {error}") from error
    if hashlib.sha256(written).hexdigest() != digest:
        raise SystemExit(f"{destination}: SHA-256 mismatch after writing the entry")

    print(f"{destination} · {len(image)} bytes · SHA-256 {digest}")


if __name__ == "__main__":
    main()
