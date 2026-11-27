"""Typeset the edition, then rasterize it with FFmpeg and encode the JPEG."""

import json
import os
import subprocess
from collections import Counter
from functools import lru_cache
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageFont

BUILD = Path(__file__).resolve().parent
SIZE = 1024
INK = "#202622"
PAPER = "#f7f0df"
LIGHT = "#fffaf0"
RULE = "#c9bfaa"
MUTED = "#57584e"
FONT_ROOT = Path("/usr/share/fonts/truetype")
FONT_DIR = next(directory for directory in (FONT_ROOT / "liberation", FONT_ROOT / "liberation2")
                if (directory / "LiberationSans-Regular.ttf").exists())

# Simplified longitude/latitude coastlines for the dot mask.
LAND = [
    [(-168,66),(-154,72),(-123,72),(-104,77),(-79,72),(-62,61),(-58,50),
     (-75,41),(-81,26),(-97,21),(-87,16),(-80,8),(-94,15),(-108,24),
     (-118,33),(-128,50),(-150,59),(-165,56)],
    [(-74,77),(-54,83),(-22,79),(-32,67),(-48,59),(-62,65)],
    [(-80,9),(-69,12),(-58,6),(-48,-1),(-35,-6),(-40,-16),(-53,-27),
     (-64,-41),(-68,-55),(-76,-48),(-73,-25),(-81,-8)],
    [(-10,36),(-10,44),(1,51),(16,55),(28,70),(51,71),(74,73),(98,76),
     (124,73),(145,71),(177,66),(165,56),(145,51),(138,42),(125,40),
     (121,30),(109,21),(105,8),(99,17),(91,22),(81,8),(73,18),(66,25),
     (57,26),(51,14),(43,12),(35,30),(26,38),(17,42),(12,37),(5,44)],
    [(-17,15),(-12,28),(-5,36),(12,37),(32,31),(42,13),(51,11),(42,-2),
     (38,-17),(32,-29),(19,-35),(11,-26),(12,-13),(7,5),(-5,5),(-16,11)],
    [(95,5),(109,3),(116,7),(119,-4),(135,-4),(151,-8),(144,-11),
     (122,-9),(105,-7),(98,-2)],
    [(113,-22),(125,-15),(136,-12),(143,-11),(153,-27),(150,-38),
     (139,-39),(130,-32),(115,-35)],
    [(131,32),(139,36),(144,45),(146,41),(141,34)],
    [(47,-13),(50,-16),(46,-25),(43,-24)],
    [(166,-45),(172,-41),(177,-35),(178,-40),(170,-47)],
    [(-8,50),(-6,57),(0,59),(2,52)],
]


def inside(lon, lat, polygon):
    crossed = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > lat) != (by > lat):
            if lon < ax + (bx - ax) * (lat - ay) / (by - ay):
                crossed = not crossed
    return crossed


@lru_cache
def font(size, serif, bold):
    family = "LiberationSerif" if serif else "LiberationSans"
    weight = "Bold" if bold else "Regular"
    return ImageFont.truetype(str(FONT_DIR / f"{family}-{weight}.ttf"), size)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def within(box, outer):
    return outer[0] <= box[0] <= box[2] <= outer[2] and outer[1] <= box[1] <= box[3] <= outer[3]


class Page:
    def __init__(self):
        self.elements = []
        self.text_boxes = []
        self.panels = {}
        self.extent = (0, 0, SIZE, SIZE)

    def panel(self, name, x, y, w, h):
        box = (x, y, x + w, y + h)
        assert within(box, self.extent), (name, box)
        for other, occupied in self.panels.items():
            assert not overlaps(box, occupied), (name, other)
        self.panels[name] = box
        return box

    def rect(self, x, y, w, h, color):
        assert within((x, y, x + w, y + h), self.extent)
        self.elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')

    def dot(self, x, y, r, color):
        assert within((x-r, y-r, x+r, y+r), self.extent)
        self.elements.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def line(self, x, y, to_x, to_y, color):
        assert within((min(x, to_x), min(y, to_y), max(x, to_x), max(y, to_y)), self.extent)
        self.elements.append(f'<path d="M{x},{y} L{to_x},{to_y}" stroke="{color}" fill="none"/>')

    def text(self, box, x, baseline, value, size, *, bold=False, serif=False, color=INK, align="start"):
        face = font(size, serif, bold)
        advance = face.getlength(value)
        origin = x - {"start": 0, "middle": advance / 2, "end": advance}[align]
        left, top, right, bottom = face.getbbox(value, anchor="ls")
        bounds = (origin + min(0, left), baseline + top, origin + max(right, advance), baseline + bottom)
        assert within(bounds, box), (value, bounds, box)
        for other, occupied in self.text_boxes:
            assert not overlaps(bounds, occupied), (value, other)
        self.text_boxes.append((value, bounds))
        family = "Liberation Serif" if serif else "Liberation Sans"
        weight = "bold" if bold else "normal"
        self.elements.append(
            f'<text x="{x}" y="{baseline}" text-anchor="{align}" font-family="{family}" '
            f'font-weight="{weight}" font-size="{size}" fill="{color}">{escape(value)}</text>'
        )

    def svg(self):
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}">\n' + (
            "\n".join(self.elements) + "\n</svg>\n"
        )


def header(page, data, stories):
    labels = data["labels"]
    region_counts = Counter(story["region"] for story in stories)
    field_count = len({story["field"] for story in stories})
    mast = page.panel("masthead", 28, 12, 968, 83)
    page.rect(28, 12, 968, 5, INK)
    page.text(mast, 31, 78, data["masthead"], 57, serif=True, bold=True)
    page.text(mast, 994, 77, data["dateline"], 22, serif=True, bold=True, align="end")
    page.rect(28, 94, 968, 1, RULE)

    strip = page.panel("counts", 28, 101, 968, 32)
    page.rect(28, 101, 968, 32, INK)
    for index, (label, count) in enumerate(zip(labels["counts"], (len(stories), len(region_counts), field_count))):
        x = 28 + index * 323
        if index:
            page.rect(x, 107, 1, 20, "#788278")
        page.text(strip, x + 126, 124, str(count), 23, serif=True, bold=True, color=LIGHT, align="end")
        page.text(strip, x + 137, 123, label, 13, bold=True, color=LIGHT)

    regions = page.panel("region key", 28, 138, 968, 21)
    for index, (name, (color, _)) in enumerate(data["regions"].items()):
        x = 28 + 108 * index
        width = min(104, 996 - x)
        page.rect(x, 138, width, 21, color)
        page.text((x+2, 138, x+width-2, 159), x + width/2, 152,
                  f"{name} {region_counts[name]}", 11, bold=True, color=LIGHT, align="middle")

    timeline = page.panel("timeline", 28, 168, 968, 52)
    page.text(timeline, 28, 181, labels["timeline"], 12, bold=True)
    page.text(timeline, 28, 199, labels["timeline_note"], 10, color=MUTED)
    for index, (time, event) in enumerate(data["timeline"]):
        x = 214 + index * 130
        page.rect(x - 9, 170, 1, 34, RULE)
        cell = (x, 168, x + 119, 205)
        page.text(cell, x, 183, time, 15, bold=True, color="#8b3f2d")
        page.text(cell, x, 200, event, 10, bold=True)
    page.rect(28, 214, 968, 2, INK)


def draw_diagram(page, x, y, diagram, color):
    box = (x, y, x + 121, y + 117)
    page.rect(x, y, 121, 117, "#eee5d2")
    center = x + 60.5
    kind = diagram["kind"]
    if kind == "migration":
        page.text(box, x + 9, y + 22, diagram["label"], 11, bold=True, color=color)
        peak = max(value for value, _ in diagram["series"])
        for index, (value, name) in enumerate(diagram["series"]):
            baseline = y + 47 + index * 32
            page.text(box, x + 9, baseline, name, 11, bold=True)
            page.rect(x + 9, baseline + 6, 102 * value / peak, 6, color if index == 0 else "#9788a4")
        return

    page.text(box, center, y + 51, diagram["metric"], 31, serif=True, bold=True, color=color, align="middle")
    page.text(box, center, y + 73, diagram["label"], 10, bold=True, align="middle")
    page.rect(x + 10, y + 84, 101, 1, RULE)
    if "followup" in diagram:
        page.text(box, center, y + 102, diagram["followup"], 11, align="middle")
    else:
        for offset in (-13, 13):
            page.dot(center + offset, y + 96, 3, color)
            page.rect(center + offset - 5, y + 101, 10, 5, color)


def leads(page, data):
    section = page.panel("lead heading", 28, 221, 968, 25)
    page.text(section, 28, 238, data["labels"]["leads"], 12, bold=True)
    for index, story in enumerate(data["leads"]):
        x, y = 28 + 490 * (index % 2), 249 + 163 * (index // 2)
        box = page.panel(f"lead {index + 1}", x, y, 478, 155)
        color, _ = data["regions"][story["region"]]
        page.rect(x, y, 478, 155, LIGHT)
        page.rect(x, y, 478, 3, color)
        page.rect(x, y + 154, 478, 1, RULE)
        draw_diagram(page, x + 10, y + 28, story["diagram"], color)
        column = (x + 143, y + 6, x + 469, y + 150)
        page.text(column, x + 144, y + 21, f"{index + 1:02}  /  {story['region'].upper()}",
                  11, bold=True, color=color)
        for row, line in enumerate(story["headline"]):
            page.text(column, x + 144, y + 48 + 25 * row, line, 26, bold=True, serif=True)
        page.text(column, x + 144, y + 94, story["caption"], 12, bold=True)
        for row, fact in enumerate(story["facts"]):
            page.text(column, x + 144, y + 112 + 15 * row, fact, 12)


def world_map(page, data, stories):
    box = page.panel("world map", 28, 577, 388, 272)
    page.text(box, 28, 599, data["labels"]["map"], 16, bold=True, serif=True)
    frame = (28, 610, 416, 823)
    page.rect(28, 610, 388, 213, "#e7ece4")

    def project(lon, lat):
        return round(222 + lon * 1.015, 1), round(716 - lat * 1.12, 1)

    for lat in range(-45, 76, 30):
        x, y = project(-179, lat)
        page.line(x, y, project(179, lat)[0], y, "#d6dfd6")
    for lon in range(-150, 151, 30):
        x, y = project(lon, 82)
        page.line(x, y, x, project(lon, -58)[1], "#d6dfd6")
    for lat in range(-57, 84, 3):
        for lon in range(-177, 179, 3):
            if any(inside(lon, lat, polygon) for polygon in LAND):
                page.dot(*project(lon, lat), 0.85, "#8e9e8d")

    pins = []
    for index, story in enumerate(stories, 1):
        x, y = project(*story["location"])
        dx, dy = story.get("pin_offset", (0, 0))
        px, py = x + dx, y + dy
        radius = 9 if index <= len(data["leads"]) else 8
        pin_box = (px - radius, py - radius, px + radius, py + radius)
        assert within(pin_box, frame), (index, pin_box)
        for other, occupied in pins:
            assert not overlaps(pin_box, occupied), (index, other, pin_box, occupied)
        pins.append((index, pin_box))
        color, _ = data["regions"][story["region"]]
        if (dx, dy) != (0, 0):
            page.line(x, y, px, py, color)
            page.dot(x, y, 1.8, color)
    for (index, (left, top, right, bottom)), story in zip(pins, stories):
        px, py = (left + right) / 2, (top + bottom) / 2
        page.dot(px, py, right - px, LIGHT)
        page.dot(px, py, right - px - 1.2, data["regions"][story["region"]][0])
        page.text((left, top, right, bottom), px, py + 3.1, str(index), 9, bold=True,
                  color=LIGHT, align="middle")
    page.text(box, 28, 841, data["labels"]["map_note"], 11, color=MUTED)


def briefs(page, data):
    box = page.panel("world briefs", 430, 577, 566, 272)
    page.text(box, 430, 599, data["labels"]["briefs"], 16, bold=True, serif=True)
    for index, story in enumerate(data["briefs"]):
        y = 610 + index * 19
        color, tag = data["regions"][story["region"]]
        page.rect(430, y, 566, 18, LIGHT if index % 2 == 0 else "#efe8d7")
        page.rect(453, y + 2, 84, 14, color)
        page.text((430, y, 450, y+18), 441, y+13, str(index + len(data["leads"]) + 1),
                  11, bold=True, color=color, align="middle")
        page.text((454, y+2, 536, y+16), 495, y+12, tag, 9, bold=True, color=LIGHT, align="middle")
        page.text((544, y, 992, y+18), 545, y+13, story["text"], 13)


def footer(page, data):
    box = page.panel("date check", 28, 855, 968, 105)
    page.rect(28, 855, 968, 2, INK)
    page.rect(28, 864, 968, 96, "#eee2cd")
    page.rect(28, 864, 4, 96, "#8b3f2d")
    page.text(box, 43, 885, data["labels"]["exclusions"], 13, bold=True, color="#783b2b")
    for index, item in enumerate(data["exclusions"]):
        x = 43 + 475 * (index // 3)
        y = 906 + 18 * (index % 3)
        page.dot(x + 3, y - 4, 1.7, "#8b3f2d")
        page.text((x+10, 891, x+462, 954), x+12, y, item, 13)
    notes = page.panel("methodology and sources", 28, 968, 968, 45)
    for index, note in enumerate(data["footer"]):
        page.text(notes, 28, 981 + 17 * index, note, 12, color=MUTED)
    page.rect(28, 1011, 968, 2, INK)


def main():
    data = json.loads((BUILD / "svg-data.json").read_text(encoding="utf-8"))
    stories = data["leads"] + data["briefs"]
    page = Page()
    page.rect(0, 0, SIZE, SIZE, PAPER)
    header(page, data, stories)
    leads(page, data)
    world_map(page, data, stories)
    briefs(page, data)
    footer(page, data)

    svg = BUILD / "front.svg"
    png = BUILD / "front.png"
    svg.write_text(page.svg(), encoding="utf-8")
    with TemporaryDirectory(prefix="news-font-cache-") as cache:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(svg),
                        "-frames:v", "1", "-threads", "1", str(png)],
                       env={**os.environ, "XDG_CACHE_HOME": cache}, check=True)
    destination = BUILD.parent / "entry.jpg"
    with Image.open(png) as frame:
        assert frame.size == (SIZE, SIZE)
        frame.convert("RGB").save(destination, quality=97, subsampling=0, optimize=True)
    assert destination.stat().st_size <= 1024 * 1024
    print(f"{destination.name}: {destination.stat().st_size} bytes")


if __name__ == "__main__":
    main()
