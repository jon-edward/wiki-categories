"""
Main CLI entrypoint for categories. See README.md or `python3 categories --help` for help.
"""

import argparse
import json
import logging
import os
import pathlib
import urllib.parse
import shutil
import sys
from typing import Optional

import requests

from process_categories import process_categories
from gzip_buffer import read_buffered_gzip_remote
from html_indices import generate_indices
from parse import parse_category_links, parse_pages, split_lines


DEFAULT_DEST = pathlib.Path(__file__).parent.parent.joinpath("pages")
GH_PAGES_URL = os.environ.get("GH_PAGES_URL", "")


def _is_redundant(
    run_info_url: str,
    _category_links_modified: Optional[str],
    _pages_modified: Optional[str],
) -> bool:
    """
    Check if current run is redundant to the last run.

    The run is redundant if all assets used in the current and most recent run
    have the same 'Last-Modified' response
    headers.
    """

    if _category_links_modified is None or _pages_modified is None:
        return False

    try:
        run_info_json = requests.get(run_info_url, timeout=10).json()
    except requests.exceptions.JSONDecodeError:
        return False

    try:
        old_category_links_modified = run_info_json["categoryLinksModified"]
        old_pages_modified = run_info_json["pagesModified"]
    except KeyError:
        return False

    return (
        old_category_links_modified == _category_links_modified
        and old_pages_modified == _pages_modified
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "categories", description="Collect category information and output to folder."
    )

    parser.add_argument("language", help="The wiki language to collect categories for.")

    parser.add_argument(
        "--dest",
        help="The output folder for category information. Must be empty.",
        type=pathlib.Path,
        default=DEFAULT_DEST,
    )

    parser.add_argument(
        "--excluded-parents",
        help="Ids of categories to exclude children from.",
        type=int,
        nargs="*",
    )

    parser.add_argument(
        "--excluded-article-categories",
        help="Ids of categories to exclude articles from.",
        type=int,
        nargs="*",
    )

    parser.add_argument(
        "--debug", help="Show progress and debug information.", action="store_true"
    )

    parser.add_argument(
        "--clean",
        help="Clean output folder before starting if the folder isn't empty.",
        action="store_true",
    )

    parser.add_argument(
        "--no-indices",
        help="Do not generate index.html in each folder.",
        action="store_true",
    )

    args = parser.parse_args()

    lang: str = args.language
    dest: pathlib.Path = args.dest
    debug: bool = args.debug
    clean: bool = args.clean
    no_indices: bool = args.no_indices

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    excluded_parents = args.excluded_parents
    excluded_article_categories = args.excluded_article_categories

    if clean and dest.exists():
        shutil.rmtree(dest)

    os.makedirs(dest, exist_ok=True)
    assert clean or not os.listdir(dest), f"The output folder {dest} is not empty."

    category_links_url = (
        f"https://dumps.wikimedia.org/{lang}wiki/"
        f"latest/{lang}wiki-latest-categorylinks.sql.gz"
    )
    pages_url = (
        f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-page.sql.gz"
    )

    def _gen_category_links():
        return parse_category_links(
            split_lines(read_buffered_gzip_remote(category_links_url, progress=debug))
        )

    def _gen_pages():
        return parse_pages(
            split_lines(read_buffered_gzip_remote(pages_url, progress=debug))
        )

    category_links_modified = requests.head(category_links_url, timeout=10).headers.get(
        "Last-Modified", None
    )
    pages_modified = requests.head(pages_url, timeout=10).headers.get(
        "Last-Modified", None
    )

    if GH_PAGES_URL and _is_redundant(
        urllib.parse.urljoin(GH_PAGES_URL, "run_info.json"),
        category_links_modified,
        pages_modified,
    ):
        logging.info(
            "Run is redundant, all Wiki data dump assets are up to date. Exiting."
        )
        sys.exit(0)

    categories_info = process_categories(
        dest,
        _gen_category_links,
        _gen_pages,
        excluded_parents=excluded_parents,
        excluded_article_categories=excluded_article_categories,
        progress=debug,
    )

    run_info = {
        "categoryLinksModified": category_links_modified,
        "pagesModified": pages_modified,
        **categories_info.to_json(),
    }

    with dest.joinpath("run_info.json").open("w") as f_info:
        json.dump(run_info, f_info, indent=1)

    if not no_indices:
        generate_indices(dest)
