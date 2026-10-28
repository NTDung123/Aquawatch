"""Extract source slide text, notes and image inventories without changing PPTX files."""

import argparse
import hashlib
import json
import posixpath
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"


def relations(archive, path):
    directory, name = posixpath.split(path)
    rel_path = posixpath.join(directory, "_rels", name + ".rels")
    if rel_path not in archive.namelist():
        return {}
    return {
        element.attrib["Id"]: {
            "target": posixpath.normpath(posixpath.join(directory, element.attrib["Target"])),
            "type": element.attrib["Type"].rsplit("/", 1)[-1],
        }
        for element in ET.fromstring(archive.read(rel_path)).findall(REL)
        if element.attrib.get("TargetMode") != "External"
    }


def paragraphs(root):
    return [
        "".join(t.text or "" for t in paragraph.iter()
                if t.tag in {"{" + NS["a"] + "}t", "{" + NS["m"] + "}t"})
        for paragraph in root.findall(".//a:p", NS)
        if paragraph.findall(".//a:t", NS) or paragraph.findall(".//m:t", NS)
    ]


def extract(path):
    with ZipFile(path) as archive:
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        links = relations(archive, "ppt/presentation.xml")
        slides = []
        for number, slide_id in enumerate(presentation.findall("p:sldIdLst/p:sldId", NS), 1):
            slide_path = links[slide_id.attrib["{" + NS["r"] + "}id"]]["target"]
            root = ET.fromstring(archive.read(slide_path))
            slide_links = relations(archive, slide_path)
            notes = []
            for link in slide_links.values():
                if link["type"] == "notesSlide":
                    note_root = ET.fromstring(archive.read(link["target"]))
                    for shape in note_root.findall(".//p:sp", NS):
                        placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
                        if placeholder is not None and placeholder.attrib.get("type") in {
                            "sldNum", "hdr", "ftr", "dt", "sldImg"
                        }:
                            continue
                        notes.extend(paragraphs(shape))
            images = []
            for picture in root.findall(".//p:pic", NS):
                blip = picture.find(".//a:blip", NS)
                image_id = blip.attrib.get("{" + NS["r"] + "}embed") if blip is not None else None
                properties = picture.find("p:nvPicPr/p:cNvPr", NS)
                if image_id in slide_links:
                    images.append({
                        "path": slide_links[image_id]["target"],
                        "description": properties.attrib.get("descr", "") if properties is not None else "",
                    })
            equations = [ET.tostring(equation, encoding="unicode")
                         for equation in root.findall(".//m:oMath", NS)]
            slides.append({"number": number, "part": slide_path, "paragraphs": paragraphs(root),
                           "equations_omml_xml": equations,
                           "notes": notes, "images": images})
    return {"file": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "slide_count": len(slides), "slides": slides}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs")
    parser.add_argument("--media-dir", type=Path, help="Optionally extract original embedded images for inspection")
    arguments = parser.parse_args()
    inputs = arguments.inputs or [Path.home() / "Desktop" / f"Lecture{n}.pptx" for n in range(1, 5)]
    result = [extract(path) for path in inputs]
    if arguments.media_dir:
        for path in inputs:
            target = arguments.media_dir / path.stem
            target.mkdir(parents=True, exist_ok=True)
            with ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.startswith("ppt/media/") and not name.endswith("/"):
                        (target / posixpath.basename(name)).write_bytes(archive.read(name))
    arguments.output.mkdir(parents=True, exist_ok=True)
    (arguments.output / "lectures_extracted.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["Text and math tokens in source order. Native equation XML is preserved in lectures_extracted.json.",
             "Embedded image content requires visual inspection; image filenames are listed per slide.", ""]
    for deck in result:
        lines.extend([f"# {Path(deck['file']).name} ({deck['slide_count']} slides)", f"SHA-256: {deck['sha256']}", ""])
        for slide in deck["slides"]:
            lines.extend([f"## Slide {slide['number']}", *slide["paragraphs"]])
            if slide["notes"]:
                lines.extend(["### Notes", *slide["notes"]])
            if slide["images"]:
                lines.append("### Images: " + ", ".join(image["path"] for image in slide["images"]))
            lines.append("")
    (arguments.output / "lectures_extracted.txt").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps([{"file": Path(d["file"]).name, "slides": d["slide_count"],
                       "image_count": sum(len(s["images"]) for s in d["slides"]),
                       "notes_slides": sum(bool(s["notes"]) for s in d["slides"])} for d in result], ensure_ascii=False))


if __name__ == "__main__":
    main()
