"""
The CLI for serializing the Wikipedia category tree. Use `python3 categories --help` for options.

Useful ids for trimming the English Wikipedia:

* 15961454    - Hidden Categories
* 869270      - Stub Categories
* 43077354    - All Stub Articles

The .category file format is a compact binary file structure for storing category information, described as follows:

* (4 bytes) name_bytes_len
* utf-8 string of the category title, of byte length name_bytes_len
* (4 bytes) predecessors_bytes_len
* Unsigned int32 list of predecessor ids, of byte length predecessors_bytes_len
* (4 bytes) successors_bytes_len
* Unsigned int32 list of successor ids, of byte length successors_bytes_len
* Unsigned int32 list of article ids, to EOF

The .index file format is an unsigned int32 list of category ids or container directory names. File operations become
more challenging as the directory becomes extremely large, so this subdivides the large category tree into chunks.
The container dir name for a given `category_id` is `category_id % 2_000`.
"""

import argparse
import os
import pathlib

from process_categories import process_categories
from gzip_buffer import read_buffered_gzip_local, read_buffered_gzip_remote
from parse import parse_category_links, parse_pages, split_lines


DEFAULT_DEST = pathlib.Path(__file__).parent.parent.joinpath("pages")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("categories", description="Collect category information and output to folder.")

    parser.add_argument("language", help="The wiki language to collect categories for.")

    parser.add_argument(
        "--dest",
        help="The output folder for category information. Must be empty.",
        type=pathlib.Path,
        default=DEFAULT_DEST)

    parser.add_argument(
        "--excluded-parents",
        help="Ids of categories to exclude children from.",
        type=int,
        nargs="*"
    )

    parser.add_argument(
        "--excluded-article-categories",
        help="Ids of categories to exclude articles from.",
        type=int,
        nargs="*"
    )

    args = parser.parse_args()

    lang: str = args.language
    dest: pathlib.Path = args.dest

    excluded_parents = args.excluded_parents
    excluded_article_categories = args.excluded_article_categories

    os.makedirs(dest, exist_ok=True)
    assert not len(os.listdir(dest)), f"The output folder {dest} is not empty."

    def gen_category_links():
        url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-categorylinks.sql.gz"
        return parse_category_links(split_lines(read_buffered_gzip_remote(url)))

    def gen_pages():
        url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-page.sql.gz"
        return parse_pages(split_lines(read_buffered_gzip_remote(url)))

    process_categories(
        dest,
        gen_category_links,
        gen_pages,
        excluded_parents=excluded_parents,
        excluded_article_categories=excluded_article_categories
    )
