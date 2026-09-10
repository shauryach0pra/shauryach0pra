#!/usr/bin/env python3
"""Post-process the generated profile-3d-contrib SVG(s) so that
visually-similar language colors (e.g. HTML's orange vs. Jupyter
Notebook's orange) don't get blended together in the language legend
and pie chart.

GitHub-Profile-3D-Contrib pulls each language's color straight from
GitHub's linguist data, which isn't configurable via the action's
SETTING_JSON. This script runs *after* the action generates the SVG
and swaps in a distinct color for any language whose official color
is too close to another language already in the chart.
"""
import re
import sys

# Distinct fallback colors to draw from when two languages collide.
# Picked to be far apart from each other and from common linguist
# colors (JS yellow, TS/Python blue, HTML/C orange-red, etc).
FALLBACK_PALETTE = [
    "#9b59b6",  # purple
    "#1abc9c",  # teal
    "#e91e63",  # pink
    "#2ecc71",  # emerald
    "#3498db",  # sky blue
    "#f1c40f",  # yellow
    "#8e44ad",  # violet
    "#16a085",  # dark teal
]

# Below this distance, two colors are considered visually indistinguishable.
THRESHOLD = 55

TITLE_PATTERN = re.compile(
    r'<path\b[^>]*?(?:fill="(#[0-9a-fA-F]{3,6})"'
    r'|style="[^"]*fill:\s*(#[0-9a-fA-F]{3,6})[^"]*")[^>]*>'
    r'.*?<title>([^<0-9][^<]*?)\s+\d+</title>',
    re.DOTALL,
)


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_distance(c1, c2):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    rmean = (r1 + r2) / 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return (
        (2 + rmean / 256) * dr ** 2
        + 4 * dg ** 2
        + (2 + (255 - rmean) / 256) * db ** 2
    ) ** 0.5


def find_languages(content):
    found = []
    for m in TITLE_PATTERN.finditer(content):
        color = (m.group(1) or m.group(2)).lower()
        lang = m.group(3).strip()
        found.append((lang, color))
    return found


def plan_replacements(found):
    used_colors = {color for _, color in found}
    replacements = {}
    for i in range(len(found)):
        for j in range(i + 1, len(found)):
            lang_a, color_a = found[i]
            lang_b, color_b = found[j]
            if color_a in replacements or color_b in replacements:
                continue
            if color_distance(color_a, color_b) >= THRESHOLD:
                continue
            for candidate in FALLBACK_PALETTE:
                candidate = candidate.lower()
                if candidate in used_colors or candidate in replacements.values():
                    continue
                if all(color_distance(candidate, c) >= THRESHOLD for _, c in found):
                    replacements[color_b] = candidate
                    used_colors.add(candidate)
                    print(
                        f"    -> recoloring {lang_b} ({color_b}) to {candidate} "
                        f"(too close to {lang_a}'s {color_a})"
                    )
                    break
    return replacements


def process(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    found = find_languages(content)
    if not found:
        print(f"  no language legend found in {path}, skipping")
        return

    print(f"  languages found in {path}:")
    for lang, color in found:
        print(f"    {lang}: {color}")

    replacements = plan_replacements(found)
    if not replacements:
        print("  no clashing colors detected")
        return

    for old, new in replacements.items():
        content = re.sub(re.escape(old), new, content, flags=re.IGNORECASE)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  updated {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fix-language-colors.py <svg-file> [<svg-file> ...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        print(f"Processing {p}")
        process(p)
