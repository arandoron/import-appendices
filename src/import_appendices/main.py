import os
import re
from pathlib import Path
from typing import Annotated

import nh3
import pypandoc
import typer
from bs4 import BeautifulSoup, Tag

from . import crud as c

app = typer.Typer()

# base path where images from documents are extracted to
BASE_MEDIA_PATH = "../../../frontend/static/images/appendices"
# base path where static images are stored for access in components
BASE_STATIC_PATH = "./images/appendices"


@app.command()
def import_document(
    file: Annotated[Path, typer.Argument(help="Path to the Word document")],
    question_id: Annotated[
        int,
        typer.Argument(help="ID of the question this document belongs to"),
    ],
    fix_paragraphs: Annotated[
        bool,
        typer.Option(
            help="Fix split paragraphs (experimental feature, output needs to be checked for accuracy)",
        ),
    ] = True,
):
    """
    Import a Word document (.docx) into the database.
    """

    if not file.exists():
        raise typer.BadParameter(f"File '{file}' does not exist")

    file_name, file_extension = get_file_name_and_extension(file)

    if file_extension != ".docx":
        raise typer.BadParameter(
            f"Incompatible file format. Got '{file_extension}', expected '.docx'"
        )

    html = convert_docx_to_html(file, file_name)
    html = santize_html(html)
    sections = process_html(html, file_name, fix_paragraphs)

    if c.check_question_for_sections(question_id):
        c.delete_all_sections_for_question(question_id)

    for section in sections:
        c.create_section(question_id, section)


def convert_docx_to_html(file: Path, file_name: str):
    """
    Convert the document into an HTML string.

    Images contained in the document are extracted and placed into a separate document folder inside
    the frontends static directory.
    """

    media_path = f"{BASE_MEDIA_PATH}/{file_name}"

    remove_existing_media(media_path)

    return pypandoc.convert_file(
        source_file=file,
        to="html5",
        format="docx",
        extra_args=[f"--extract-media={media_path}", "--standalone=false"],
    )


def get_file_name_and_extension(file: Path):
    """
    Return the normalized file name and its extension.
    """

    normalized_file_name = file.stem.lower().replace(" ", "-")

    return normalized_file_name, file.suffix


def remove_existing_media(media_path: str):
    """
    Check if media directory for this document already exists. If so, delete all its files and the
    media subdirectory.
    """

    if os.path.isdir(media_path):
        path = f"{media_path}/media"

        for file in os.listdir(path):
            os.remove(f"{path}/{file}")

        # remove now empty /media subdirectory
        os.rmdir(path)


def santize_html(html: str):
    """
    Sanitize an HTML string.
    """

    allowed_tags = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "br",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "img",
        "figure",
        "figcaption",
        "a",
        "strong",
        "em",
        "b",
        "i",
        "ul",
        "ol",
        "li",
        "div",
        "span",
    }
    allowed_attributes = {
        "img": {
            "src",
            "alt",
        },
        "a": {
            "href",
        },
        "span": {
            "class",
        },
    }
    allowed_schemes = {"http", "https"}

    return nh3.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        url_schemes=allowed_schemes,
    )


def process_html(
    html: str, file_name: str, fix_paragraphs: bool
) -> list[dict[str, str | None]]:
    """
    Apply different processing steps on the HTML, preparing it for insertion into the Database.

    Steps: remove newlines in HTML string, add CSS classes for styling in the frontend, fix image
    hrefs and split content into distinct sections for storing.
    """

    html = html.replace("\n", " ")

    soup = BeautifulSoup(html, "html.parser")

    set_css_classes(soup)
    set_image_sources(soup, file_name)
    return get_sections(soup, fix_paragraphs)


def get_sections(
    soup: BeautifulSoup, fix_paragraphs: bool
) -> list[dict[str, str | None]]:
    """
    Split HTML string into sections based on <h2>-elements.
    """

    sections: list[dict[str, str | None]] = []
    headers = soup.find_all("h2")

    for i, header in enumerate(headers):
        # get header text and remove all number from it
        current_header = re.sub(r"\d+", "", header.get_text(strip=True))
        section_content = []

        for sibling in header.next_siblings:
            # if at next section header, stop
            if i + 1 < len(headers) and sibling == headers[i + 1]:
                break

            if isinstance(sibling, Tag):
                section_content.append(str(sibling))

        content = "".join(section_content).strip()

        if fix_paragraphs:
            content = fix_split_paragraphs(content)

        sections.append(
            {
                "id": f"{i + 1}",
                "header": current_header,
                "content": content,
            }
        )

    return sections


def fix_split_paragraphs(section: str):
    """
    Fix paragraph issues caused by conversion from Word documents with pages.

    This is needed because in Word documents, paragraphs can be split up (e.g. by images, tables,
    pagebreaks etc.). When reading in a document this makes sense, however on a website, it leads to
    a worse reading flow, when paragraphs stop in the middle of a sentence and are resumed in a new
    paragraph or after an image.
    """

    # accepted values for last character of a paragraph
    punctuation_marks = (".", ":", "!", "?", ")", "]", "}", "'", '"')

    soup = BeautifulSoup(section, "html.parser")
    paragraphs = soup.find_all("p")

    for i, paragraph in enumerate(paragraphs):
        if not paragraph.text.endswith(punctuation_marks):
            # only consider paragraphs on the same level (sibling) as continuation for current paragraph
            for sibling in paragraph.next_siblings:
                if isinstance(sibling, Tag):
                    # check whether paragraph contains converted math equation/formula; if this is the
                    # case, then skip joining the following paragraph
                    sibling_has_math_child = any(
                        isinstance(child, Tag)
                        and child.name == "span"
                        and child.has_attr("class")
                        and "math" in child["class"]
                        for child in paragraph.children
                    )
                    if sibling_has_math_child:
                        break

                    # don't join paragraphs if there's a heading between them, they probably don't
                    # belong to each other
                    match sibling.name:
                        case "h3":
                            break
                        case "h4":
                            break
                        case "h5":
                            break
                        case "h6":
                            break
                        case "p":
                            paragraph.string = f"{paragraph.text} {sibling.text}"

                            # remove joined paragraph from HTML, continue until joined paragraph
                            # itself ends with proper punctuation
                            if not sibling.text.endswith(punctuation_marks):
                                sibling.decompose()
                            else:
                                sibling.decompose()
                                break

    return soup.decode()


def set_css_classes(soup: BeautifulSoup):
    """
    Add CSS classes to selected types of elements.
    """

    tag_names = {"table", "figure", "img", "figcaption", "ul", "ol"}

    for name in tag_names:
        for element in soup.find_all(name):
            element["class"] = f"appendix-document-{name}"


def set_image_sources(soup: BeautifulSoup, file_name: str):
    """
    Set src attribute for image elements to match frontend static path and add alt texts where possible.
    """

    src_path = f"{BASE_STATIC_PATH}/{file_name}/media"

    images = soup.find_all("img")

    for i, image in enumerate(images):
        # images extracted by pandoc are all named "image1.png", "image2.png", ... in the order they
        # are encountered in the document
        image["src"] = f"{src_path}/image{i + 1}.png"

        parent = image.parent
        if parent:
            figcaption = parent.find("figcaption")
            if figcaption:
                image["alt"] = figcaption.get_text(strip=True)
        else:
            image["alt"] = ""


if __name__ == "__main__":
    app()
