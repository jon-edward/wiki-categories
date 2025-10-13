import ast
import dataclasses
import re
from typing import Iterable

# Define regex components for parsing SQL insert statements
_STRING_VALUE = r"(?:'[^'\\]*(?:\\.[^'\\]*)*')"
_OPTIONAL_STRING = rf"(?:{_STRING_VALUE}|NULL)"
_INTEGER_VALUE = r"(?:\d+)"
_FLOAT_VALUE = r"(?:\d+\.\d+)"
_ARTICLE_OR_CATEGORY_NS = r"(?:0|14)"
_PAGE_OR_SUBCAT = r"(?:page|subcat)"

# A subset of the the fields in the SQL insert statements are parsed into dataclasses.


@dataclasses.dataclass(slots=True)
class CategoryLink:
    """
    A deserialized entry within a category links SQL script.
    """

    cl_from: int
    cl_type: str
    cl_target_id: int

    @property
    def is_page(self) -> bool:
        return self.cl_type == "page"

    @property
    def is_subcategory(self) -> bool:
        return self.cl_type == "subcat"


@dataclasses.dataclass(slots=True)
class Page:
    """
    A deserialized entry within a pages SQL script.
    """

    page_id: int
    page_namespace: int
    page_title: str

    @property
    def is_article(self) -> bool:
        return self.page_namespace == 0

    @property
    def is_category(self) -> bool:
        return self.page_namespace == 14


@dataclasses.dataclass(slots=True)
class LinkTarget:
    """
    A deserialized entry within a link targets SQL script.
    """

    lt_id: int
    lt_title: str


def split_lines(buffered_content: Iterable[bytes]) -> Iterable[bytes]:
    """
    Consume the buffered content and split into lines at the '\n' line seperator.
    """

    sep = b"\n"

    line_buffer = b""

    for content in buffered_content:
        lines = content.split(sep)

        lines[0] = line_buffer + lines[0]
        line_buffer = lines.pop()
        yield from lines

    yield line_buffer


def _parse(pattern: re.Pattern, lines: Iterable[bytes]) -> Iterable[re.Match]:
    """Apply the given regex pattern to each line and yield all matches, ignoring decode errors."""
    for line in lines:
        line_str = line.decode("utf-8", errors="ignore")
        yield from pattern.findall(line_str)


def parse_link_targets(lines: Iterable[bytes]) -> Iterable[LinkTarget]:
    """
    Deserialize link targets SQL script lines into LinkTarget objects.
    """

    pattern: re.Pattern = re.compile(rf"\(({_INTEGER_VALUE}),14,({_STRING_VALUE})\)")

    for match in _parse(pattern, lines):
        lt_id = int(match[0])
        lt_title = ast.literal_eval(match[1])
        yield LinkTarget(lt_id, lt_title)


def parse_pages(lines: Iterable[bytes]) -> Iterable[Page]:
    """
    Deserialize pages SQL script lines into Page objects.
    """

    pattern: re.Pattern = re.compile(
        rf"\(({_INTEGER_VALUE}),({_ARTICLE_OR_CATEGORY_NS}),"
        rf"({_STRING_VALUE}),{_INTEGER_VALUE},"
        rf"{_INTEGER_VALUE},{_FLOAT_VALUE},"
        rf"{_STRING_VALUE},{_STRING_VALUE},"
        rf"{_INTEGER_VALUE},{_INTEGER_VALUE},"
        rf"{_STRING_VALUE},{_OPTIONAL_STRING}\)"
    )

    for match in _parse(pattern, lines):
        page_id = int(match[0])
        page_namespace = int(match[1])
        page_title = ast.literal_eval(match[2])
        yield Page(page_id, page_namespace, page_title)


def parse_category_links(lines: Iterable[bytes]) -> Iterable[CategoryLink]:
    """
    Deserialize category link SQL script lines into CategoryLink objects.
    """

    pattern: re.Pattern = re.compile(
        rf"\(({_INTEGER_VALUE}),{_STRING_VALUE},{_STRING_VALUE},{_STRING_VALUE},"
        rf"'({_PAGE_OR_SUBCAT})',{_INTEGER_VALUE},({_INTEGER_VALUE})\)"
    )

    for match in _parse(pattern, lines):
        cl_from = int(match[0])
        cl_type = match[1]
        cl_target_id = int(match[2])
        yield CategoryLink(cl_from, cl_type, cl_target_id)
