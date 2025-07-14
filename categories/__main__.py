"""
Main CLI entrypoint for categories. See README.md or `python3 categories --help` for usage.
"""

import json
import logging
import os
import pathlib
from pprint import pprint
import urllib.parse
import shutil
import sys
from typing import Optional

import requests

from config import parse_config
from process_categories import process_categories
from gzip_buffer import read_buffered_gzip
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
    args = parse_config()
    pprint(args)

    if args.dev:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.clean and args.dest.exists():
        shutil.rmtree(args.dest)

    os.makedirs(args.dest, exist_ok=True)
    assert not os.listdir(args.dest), f"The output folder {args.dest} is not empty. Either delete its contents or use --clean to remove it."

    category_links_url = (
        f"https://dumps.wikimedia.org/{args.language}wiki/"
        f"latest/{args.language}wiki-latest-categorylinks.sql.gz"
    )
    pages_url = (
        f"https://dumps.wikimedia.org/{args.language}wiki/latest/{args.language}wiki-latest-page.sql.gz"
    )

    # For local development, so that you can test without downloading the dumps every run
    # Make sure to decompress the dump files first
    if args.use_cache:
        cache_dir = pathlib.Path("data_cache")
        cached_category_links = cache_dir.joinpath(f"{args.language}wiki-latest-categorylinks.sql")
        
        if cached_category_links.exists():
            category_links_url = cached_category_links
            logging.info(
                f"Using cached category links from {category_links_url}"
            )
        
        cached_pages = cache_dir.joinpath(f"{args.language}wiki-latest-page.sql")
        
        if cached_pages.exists():
            pages_url = cached_pages
            logging.info(
                f"Using cached pages from {pages_url}"
            )
        
        category_links_modified = None
        pages_modified = None
    else:
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

    def _gen_category_links():
        return parse_category_links(
            split_lines(read_buffered_gzip(category_links_url, progress=args.dev))
        )

    def _gen_pages():
        return parse_pages(
            split_lines(read_buffered_gzip(pages_url, progress=args.dev))
        )

    categories_info = process_categories(
        args,
        _gen_category_links,
        _gen_pages,
    )

    run_info = {
        "categoryLinksModified": category_links_modified,
        "pagesModified": pages_modified,
        **categories_info.to_json(),
    }

    with args.dest.joinpath("run_info.json").open("w") as f_info:
        json.dump(run_info, f_info, indent=1)

    if not args.no_indices:
        generate_indices(args.dest, args.index_root_path)
