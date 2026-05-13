#!/usr/bin/env python3
"""
convert_webp.py — Batch JPEG → WebP converter for portfolio assets

Usage:
  python3 scripts/convert_webp.py               # process link/ with defaults
  python3 scripts/convert_webp.py --dry-run     # preview without writing
  python3 scripts/convert_webp.py --force       # regenerate even if up to date

Output: {stem}_800.webp and {stem}_2000.webp alongside the source JPEGs.
Original JPEGs are never modified.
"""

import argparse
import glob
import io
import os
import sys
from PIL import Image, ImageCms

_SRGB = ImageCms.createProfile('sRGB')

def to_srgb(img):
    """埋め込み ICC プロファイルを sRGB に変換して返す。プロファイルなし／sRGB の場合はそのまま返す。"""
    icc = img.info.get('icc_profile')
    if not icc:
        return img
    try:
        src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        desc = ImageCms.getProfileDescription(src_profile).strip().lower()
        if 'srgb' in desc:
            return img
        return ImageCms.profileToProfile(img, src_profile, _SRGB, renderingIntent=0, outputMode='RGB')
    except Exception:
        return img

SIZES = [
    ("_800",  800,  78),   # mobile
    ("_2000", 2000, 82),   # desktop / retina
]

def convert(src: str, dry_run: bool, force: bool) -> list[str]:
    generated = []
    stem, _ = os.path.splitext(src)
    src_mtime = os.path.getmtime(src)

    for suffix, max_w, quality in SIZES:
        out = stem + suffix + ".webp"
        if not force and os.path.exists(out) and os.path.getmtime(out) >= src_mtime:
            continue  # already up to date
        if dry_run:
            print(f"  [dry] {os.path.relpath(out)}")
            generated.append(out)
            continue
        with Image.open(src) as img:
            img = to_srgb(img)
            w, h = img.size
            if w > max_w:
                img = img.resize((max_w, round(h * max_w / w)), Image.LANCZOS)
            img.save(out, "WEBP", quality=quality, method=6)
        generated.append(out)
        print(f"  ✓ {os.path.relpath(out)}")

    return generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src_dir", nargs="?", default="link",
                        help="Source folder (default: link/)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true",
                        help="Regenerate even if output is newer than source")
    args = parser.parse_args()

    base = os.path.join(os.path.dirname(__file__), "..", args.src_dir)
    jpgs = sorted(glob.glob(os.path.join(base, "**", "*.jpg"), recursive=True))

    if not jpgs:
        print(f"No JPEGs found in {base}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(jpgs)} JPEGs in '{args.src_dir}/'...\n")
    total = 0
    for jpg in jpgs:
        results = convert(jpg, args.dry_run, args.force)
        total += len(results)

    action = "Would generate" if args.dry_run else "Generated"
    print(f"\n{action} {total} WebP files.")


if __name__ == "__main__":
    main()
