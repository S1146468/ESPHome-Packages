"""Inspect local ESP application descriptors without connecting to hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def inspect(path):
    data = path.read_bytes()
    applications = []
    # Standard app-only image and common ESP32 factory layout, plus descriptors
    # preceded by a valid image header. Do not interpret arbitrary binary strings
    # or an ESPHome version as a Git package revision.
    marker = struct.pack("<I", 0xABCD5432)
    position = 0
    while True:
        position = data.find(marker, position)
        if position < 0:
            break
        start = position - 32
        if start >= 0 and data[start] == 0xE9 and position + 256 <= len(data):
            descriptor = data[position:position + 256]
            def text(a, b):
                return descriptor[a:b].split(b"\0", 1)[0].decode("utf-8", errors="replace")
            applications.append(dict(image_offset=start, project=text(48, 80), version=text(16, 48),
                compile_time=text(80, 96), compile_date=text(96, 112), idf=text(112, 144),
                elf_sha256=descriptor[144:176].hex()))
        position += 4
    return dict(file=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), applications=applications,
                installed_identity_verified=False, git_package_revision_recovered=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps([inspect(p) for p in args.files], indent=2) + "\n", encoding="utf-8")
