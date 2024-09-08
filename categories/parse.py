import ast
import dataclasses
import re
from typing import Iterable


_STRING_VALUE = r"'[^'\\]*(?:\\.[^'\\]*)*'"
_INTEGER_VALUE = r"\d+"
_FLOAT_VALUE = r"\d+\.\d+"


@dataclasses.dataclass
class CategoryLink:
    child_id: int
    parent_name: str
    is_article: bool


@dataclasses.dataclass
class Page:
    page_id: int
    name: str


def split_lines(buffered_content: Iterable[bytes]) -> Iterable[bytes]:
    sep = b"\n"

    line_buffer = b""

    for content in buffered_content:
        lines = content.split(sep)

        lines[0] = line_buffer + lines[0]
        line_buffer = lines.pop()

        for line in lines:
            yield line

    yield line_buffer


def parse_category_links(lines: Iterable[bytes]) -> Iterable[CategoryLink]:
    pattern: re.Pattern = re.compile(
        rf"\(({_INTEGER_VALUE}),({_STRING_VALUE}),(?:{_STRING_VALUE},){{4}}'(subcat|page)'\)"
    )

    for line in lines:
        line_str = line.decode("utf-8", errors="ignore")

        for hit in re.findall(pattern, line_str):
            child_id_str, unescaped_parent_name, page_or_subcat = hit

            child_id = int(child_id_str)
            parent_name = ast.literal_eval(unescaped_parent_name)
            is_article = page_or_subcat == "page"

            yield CategoryLink(child_id, parent_name, is_article)


def parse_pages(lines: Iterable[bytes]) -> Iterable[Page]:
    pattern: re.Pattern = re.compile(
        rf"\(({_INTEGER_VALUE}),14,"
        rf"({_STRING_VALUE}),{_INTEGER_VALUE},"
        rf"{_INTEGER_VALUE},{_FLOAT_VALUE},"
        rf"{_STRING_VALUE},{_STRING_VALUE},"
        rf"{_INTEGER_VALUE},{_INTEGER_VALUE},"
        rf"{_STRING_VALUE},(?:{_STRING_VALUE}|NULL)\)"
    )

    for line in lines:
        line_str = line.decode("utf-8", errors="ignore")

        for hit in re.findall(pattern, line_str):
            page_id_str, unescaped_name = hit
            yield Page(int(page_id_str), ast.literal_eval(unescaped_name))
