"""
Defines the command line interface for the categories processing script.
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

from categories.config import parse_config, RunConfig
from categories.process_categories import process_categories, CategoriesInfo
from categories.gzip_buffer import read_buffered_gzip
from categories.parse import parse_category_links, parse_pages, split_lines
from categories.html_indices import index_directories


GH_PAGES_URL = os.environ.get("GH_PAGES_URL", "")


def _is_redundant(
    run_info_url: str,
    _category_links_modified: Optional[str],
    _pages_modified: Optional[str],
) -> bool:
    """
    Check if current run is redundant to the last run.

    The run is redundant if all assets used in the current and most recent run
    have the same 'Last-Modified' response headers.
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


def main(config: Optional[RunConfig] = None) -> None:
    if config:
        args = config
    else:
        args = parse_config()
    
    pprint(args)

    _setup_logging(args)
    _prepare_output_dir(args)

    category_links_url, pages_url, category_links_modified, pages_modified = (
        _resolve_data_sources(args)
    )

    _exit_if_redundant(category_links_modified, pages_modified)

    categories_info = process_categories(
        args,
        lambda: parse_category_links(
            split_lines(read_buffered_gzip(category_links_url, progress=args.dev))
        ),
        lambda: parse_pages(
            split_lines(read_buffered_gzip(pages_url, progress=args.dev))
        ),
    )

    _write_run_info(args, categories_info, category_links_modified, pages_modified)

    if not args.no_indices:
        index_directories(args.dest, args.index_root_path)


def _setup_logging(args: RunConfig) -> None:
    if args.dev:
        logging.getLogger().setLevel(logging.DEBUG)


def _prepare_output_dir(args: RunConfig) -> None:
    if args.clean and args.dest.exists():
        logging.debug("Cleaning output directory: %s", args.dest)
        shutil.rmtree(args.dest)
    os.makedirs(args.dest, exist_ok=True)
    assert not os.listdir(args.dest), (
        f"The output folder {args.dest} is not empty. Either delete its contents or use --clean to remove it."
    )


def _resolve_data_sources(
    args: RunConfig,
) -> tuple[str | pathlib.Path, str | pathlib.Path, Optional[str], Optional[str]]:
    category_links_url = (
        f"https://dumps.wikimedia.org/{args.language}wiki/"
        f"latest/{args.language}wiki-latest-categorylinks.sql.gz"
    )

    pages_url = f"https://dumps.wikimedia.org/{args.language}wiki/latest/{args.language}wiki-latest-page.sql.gz"

    if args.use_cache:
        cache_dir = pathlib.Path("data_cache")
        cached_category_links = cache_dir.joinpath(
            f"{args.language}wiki-latest-categorylinks.sql"
        )

        if cached_category_links.exists():
            category_links_url = cached_category_links
            logging.info(f"Using cached category links from {category_links_url}")

        cached_pages = cache_dir.joinpath(f"{args.language}wiki-latest-page.sql")

        if cached_pages.exists():
            pages_url = cached_pages
            logging.info(f"Using cached pages from {pages_url}")

        category_links_modified = None
        pages_modified = None
    else:
        category_links_modified = requests.head(
            category_links_url, timeout=10
        ).headers.get("Last-Modified", None)
        pages_modified = requests.head(pages_url, timeout=10).headers.get(
            "Last-Modified", None
        )

    return category_links_url, pages_url, category_links_modified, pages_modified


def _exit_if_redundant(
    category_links_modified: Optional[str], pages_modified: Optional[str]
) -> None:
    if GH_PAGES_URL and _is_redundant(
        urllib.parse.urljoin(GH_PAGES_URL, "run_info.json"),
        category_links_modified,
        pages_modified,
    ):
        logging.info(
            "Run is redundant, all Wiki data dump assets are up to date. Exiting."
        )
        sys.exit(0)


def _write_run_info(
    args: RunConfig,
    categories_info: CategoriesInfo,
    category_links_modified: Optional[str],
    pages_modified: Optional[str],
) -> None:
    run_info = {
        "categoryLinksModified": category_links_modified,
        "pagesModified": pages_modified,
        **categories_info.to_json(),
    }
    with args.dest.joinpath("run_info.json").open("w") as f_info:
        json.dump(run_info, f_info, indent=1)


if __name__ == "__main__":
    main()
