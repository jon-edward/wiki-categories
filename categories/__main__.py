import argparse
import json
import logging
import os
import pathlib
import urllib.parse
from typing import Optional

import requests

from process_categories import process_categories
from gzip_buffer import read_buffered_gzip_remote
from parse import parse_category_links, parse_pages, split_lines


DEFAULT_DEST = pathlib.Path(__file__).parent.parent.joinpath("pages")
GH_PAGES_URL = os.environ.get("GH_PAGES_URL", None)


def is_redundant(run_info_url: str, _category_links_modified: Optional[str], _pages_modified: Optional[str]) -> bool:
    """
    Check if current run is redundant to the last run.

    The run is redundant if all assets used in the current and most recent run have the same 'Last-Modified' response
    headers.
    """

    if _category_links_modified is None or _pages_modified is None:
        return False

    try:
        run_info_json = requests.get(run_info_url).json()
    except requests.exceptions.JSONDecodeError:
        return False
    
    try:
        old_category_links_modified = run_info_json["categoryLinksModified"]
        old_pages_modified = run_info_json["pagesModified"]
    except KeyError:
        return False
    
    return old_category_links_modified == _category_links_modified and old_pages_modified == _pages_modified


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "categories", description="Collect category information and output to folder.")

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

    parser.add_argument(
        "--debug",
        help="Show progress and debug information.",
        action="store_true"
    )

    args = parser.parse_args()

    lang: str = args.language
    dest: pathlib.Path = args.dest
    debug: bool = args.debug

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    excluded_parents = args.excluded_parents
    excluded_article_categories = args.excluded_article_categories

    os.makedirs(dest, exist_ok=True)
    assert not len(os.listdir(dest)), f"The output folder {dest} is not empty."

    category_links_url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-categorylinks.sql.gz"
    pages_url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-page.sql.gz"

    def gen_category_links():
        return parse_category_links(split_lines(read_buffered_gzip_remote(category_links_url, progress=debug)))

    def gen_pages():
        return parse_pages(split_lines(read_buffered_gzip_remote(pages_url, progress=debug)))

    category_links_modified = requests.head(category_links_url).headers.get("Last-Modified", None)
    pages_modified = requests.head(pages_url).headers.get("Last-Modified", None)

    if GH_PAGES_URL is not None and is_redundant(urllib.parse.urljoin(GH_PAGES_URL, "run_info.json"),
                                                 category_links_modified, pages_modified):
        logging.info("Run is redundant, all Wiki data dump assets are up to date. Exiting.")
        exit(0)

    categories_info = process_categories(
        dest,
        gen_category_links,
        gen_pages,
        excluded_parents=excluded_parents,
        excluded_article_categories=excluded_article_categories,
        progress=debug
    )

    run_info = {
        "categoryLinksModified": category_links_modified,
        "pagesModified": pages_modified,
        **categories_info.to_json()
    }

    with dest.joinpath("run_info.json").open("w") as f_info:
        json.dump(run_info, f_info, indent=1)
