"""
Contains the main function entrypoint for categories.
"""

from array import array
from collections import defaultdict
import dataclasses
import datetime
from itertools import chain
import logging
import os
import pathlib
import pickle
import random
import struct
from typing import (
    Callable,
    DefaultDict,
    Iterable,
    Union,
)

import networkx as nx
import numpy as np
from tqdm import tqdm

from config import RunConfig
from parse import CategoryLink, Page

_DATETIME_STRFTIME = "%m/%d/%Y, %H:%M:%S"


def _bytes_from_uint32(val: Iterable[int]) -> bytes:
    return b"".join(struct.pack(">I", v) for v in val)


def _serialize_fields(*fields: bytes) -> bytes:
    return b"".join(len(x).to_bytes(length=4, byteorder="big") + x for x in fields)


def _serialize_category(
    name: str,
    predecessors: Iterable[int],
    successors: Iterable[int],
    articles: Iterable[int],
    article_names: Iterable[str],
) -> bytes:
    """
    Serialize a category into a compact binary format.
    The format is:
    - name: string
    - predecessors: list of predecessor category IDs (uint32)
    - successors: list of successor category IDs (uint32)
    - articles: list of article IDs (uint32)
    - article_names: list of article names (string, null-terminated)
    """
    name_bytes = name.encode()
    predecessors_bytes = _bytes_from_uint32(predecessors)
    successors_bytes = _bytes_from_uint32(successors)
    articles_bytes = _bytes_from_uint32(articles)
    article_names_bytes = b"\0".join(name.encode() for name in article_names)

    return _serialize_fields(
        name_bytes,
        predecessors_bytes,
        successors_bytes,
        articles_bytes,
        article_names_bytes,
    )


@dataclasses.dataclass
class CategoriesInfo:
    """
    Information about the completed run, will be added to `run_info.json`.
    """

    categories_count: int
    articles_count: int
    finished: datetime.datetime
    balancing_mod_operand: int

    def to_json(self) -> dict[str, Union[str, int]]:
        """
        Makes run information safe for use in a JSON file.
        """

        return {
            "categoriesCount": self.categories_count,
            "articlesCount": self.articles_count,
            "finished": self.finished.strftime(_DATETIME_STRFTIME),
            "balancingModOperand": self.balancing_mod_operand,
        }


# The following array and default dict functions are defined to allow for
# pickling of the _CategoryTreeData dataclass.
#
# Lambda functions cannot be pickled


def _array_L() -> array:
    """
    Create an array of type 'L' (unsigned long).
    """
    return array("L")


def _default_dict_L() -> DefaultDict[int, array]:
    """
    Create a default dictionary with array of type 'L' as default factory.
    """
    return defaultdict(_array_L)


@dataclasses.dataclass
class _CategoryTreeData:
    article_id_to_name: dict[int, str] = dataclasses.field(default_factory=dict)
    category_id_to_name: dict[int, str] = dataclasses.field(default_factory=dict)
    category_edges: list[tuple[int, int]] = dataclasses.field(default_factory=list)
    category_to_articles: DefaultDict[int, array] = dataclasses.field(
        default_factory=_default_dict_L
    )


def _get_category_tree_data(
    category_links_gen: Callable[[], Iterable[CategoryLink]],
    pages_gen: Callable[[], Iterable[Page]],
) -> _CategoryTreeData:
    """
    Generate category tree data from generators.
    """
    data = _CategoryTreeData()
    for page in pages_gen():
        if page.is_article:
            data.article_id_to_name[page.page_id] = page.name
        else:
            data.category_id_to_name[page.page_id] = page.name

    name_to_id = {v: k for k, v in data.category_id_to_name.items()}

    for link in category_links_gen():
        parent_id = name_to_id.get(link.parent_name, None)

        if parent_id is None:
            continue

        if link.is_article:
            article_name = data.article_id_to_name.get(link.child_id, None)
            if article_name is None:
                continue
            data.category_to_articles[parent_id].append(link.child_id)
        elif link.child_id in data.category_id_to_name:
            data.category_edges.append((parent_id, link.child_id))

    return data


def process_categories(
    config: RunConfig,
    category_links_gen: Callable[[], Iterable[CategoryLink]],
    pages_gen: Callable[[], Iterable[Page]],
) -> CategoriesInfo:
    """
    Main function of categories.
    """

    data = _get_or_load_category_tree_data(config, category_links_gen, pages_gen)

    cat_graph = _build_category_graph(data)
    excluded_categories, excluded_articles = _get_excluded(config, cat_graph, data)

    _remove_excluded_categories(cat_graph, excluded_categories)
    _remove_small_and_inaccessible(cat_graph, config, data)

    _log_exclusions(excluded_categories, excluded_articles)

    added_articles = _process_and_write_categories(
        config, cat_graph, data, excluded_articles
    )
    _write_dir_indices(config)

    categories_count = len(cat_graph)
    articles_count = len(added_articles)

    finished = datetime.datetime.now()

    logging.debug("%d total categories", categories_count)
    logging.debug("%d total articles", articles_count)
    logging.debug("Finished at %s", finished.strftime(_DATETIME_STRFTIME))

    return CategoriesInfo(
        categories_count=categories_count,
        articles_count=articles_count,
        finished=finished,
        balancing_mod_operand=config.balancing_mod_operand,
    )


def _get_or_load_category_tree_data(
    config: RunConfig,
    category_links_gen: Callable[[], Iterable[CategoryLink]],
    pages_gen: Callable[[], Iterable[Page]],
) -> _CategoryTreeData:
    """
    Load or generate category tree data, using cache if enabled.
    """
    category_tree_cached = pathlib.Path("data_cache/_cached_category_tree_data.pickle")

    if config.use_cache:
        if not os.path.exists(category_tree_cached):
            data = _get_category_tree_data(category_links_gen, pages_gen)

            with open(category_tree_cached, "wb") as f:
                pickle.dump(data, f)
                logging.debug("Cached category tree data to %s", category_tree_cached)
        else:
            with open(category_tree_cached, "rb") as f:
                data = pickle.load(f)
                logging.debug(
                    "Loaded cached category tree data from %s", category_tree_cached
                )
    else:
        data = _get_category_tree_data(category_links_gen, pages_gen)

    return data


def _build_category_graph(data: _CategoryTreeData) -> nx.DiGraph:
    """
    Build the category graph from category edges.
    """
    cat_graph = nx.DiGraph()
    cat_graph.add_edges_from(data.category_edges)
    return cat_graph


def _get_excluded(
    config: RunConfig, cat_graph: nx.DiGraph, data: _CategoryTreeData
) -> tuple[set[int], set[int]]:
    """
    Compute excluded categories and articles based on config and graph.
    """
    excluded_categories = set(
        chain(
            config.excluded_parents,
            config.excluded_grandparents,
            config.excluded_article_categories,
        )
    )

    for e in config.excluded_parents:
        if e in cat_graph:
            excluded_categories.update(cat_graph.successors(e))

    for id_ in config.excluded_grandparents:
        if id_ in cat_graph:
            for child in cat_graph.successors(id_):
                excluded_categories.add(child)
                excluded_categories.update(cat_graph.successors(child))

    excluded_articles = set()

    for a in config.excluded_article_categories:
        excluded_articles.update(data.category_to_articles[a])

    return excluded_categories, excluded_articles


def _remove_excluded_categories(
    cat_graph: nx.DiGraph, excluded_categories: set[int]
) -> None:
    """
    Remove excluded categories from the graph.
    """
    if excluded_categories:
        cat_graph.remove_nodes_from(excluded_categories)


def _get_safe_categories(G: nx.DiGraph, config: RunConfig) -> set[int]:
    """
    Get categories that are safe to keep based on the safe depth.
    """
    return set(nx.dfs_tree(G, config.root_node, depth_limit=config.safe_depth).nodes())


def _remove_contents_inaccessible(G: nx.DiGraph, config: RunConfig) -> None:
    """
    Remove nodes that are not accessible from the root node.
    """
    accessible = set(nx.dfs_tree(G, config.root_node).nodes())
    inaccessible = set(G.nodes()) - accessible
    if inaccessible:
        logging.debug(
            "Removing %d inaccessible categories from the graph.", len(inaccessible)
        )
        G.remove_nodes_from(inaccessible)


def _get_article_count_percentile(
    G: nx.DiGraph, config: RunConfig, data: _CategoryTreeData
) -> int:
    """
    Get the article count percentile for the categories in the graph.
    """
    article_counts = [len(data.category_to_articles[n]) for n in G.nodes()]
    return int(np.percentile(article_counts, config.article_count_percentile))


def _remove_small_and_inaccessible(
    cat_graph: nx.DiGraph, config: RunConfig, data: _CategoryTreeData
) -> None:
    """
    Remove small categories and inaccessible nodes from the graph.
    """
    safe_categories = _get_safe_categories(cat_graph, config)
    logging.debug("Safe categories: %d", len(safe_categories))

    min_article_count = _get_article_count_percentile(cat_graph, config, data) + 1

    small_categories = set(
        n
        for n in cat_graph.nodes()
        if len(data.category_to_articles[n]) < min_article_count
        and n not in safe_categories
    )

    if small_categories:
        logging.debug(
            "Removing %d small categories that are not safe. These categories have less than %d articles.",
            len(small_categories),
            min_article_count,
        )
        cat_graph.remove_nodes_from(small_categories)

    _remove_contents_inaccessible(cat_graph, config)


def _log_exclusions(excluded_categories: set[int], excluded_articles: set[int]) -> None:
    """
    Log excluded categories and articles.
    """
    if excluded_categories:
        logging.debug(
            "Excluding %d categories that were specified in the config.",
            len(excluded_categories),
        )

    if excluded_articles:
        logging.debug(
            "Excluding %d articles that were specified in the config.",
            len(excluded_articles),
        )


def _process_and_write_categories(
    config: RunConfig,
    cat_graph: nx.DiGraph,
    data: _CategoryTreeData,
    excluded_articles: set[int],
) -> set[int]:
    """
    Process categories and write their data to files.

    Returns the set of added articles.
    """
    added_articles = set()

    for balancing_idx in range(config.balancing_mod_operand):
        category_chunk_dir = config.dest.joinpath(str(balancing_idx))
        category_chunk_dir.mkdir()

    for category in tqdm(
        cat_graph, disable=not config.dev, desc="Processing categories"
    ):
        name = data.category_id_to_name[category]
        predecessors = cat_graph.predecessors(category)
        successors = cat_graph.successors(category)
        category_chunk_dir = config.dest.joinpath(
            str(category % config.balancing_mod_operand)
        )

        articles = [
            a
            for a in data.category_to_articles[category]
            if a not in excluded_articles and a in data.article_id_to_name
        ]

        if (
            len(articles) > config.max_articles_per_category
            and config.max_articles_per_category != -1
        ):
            articles = random.sample(articles, config.max_articles_per_category)

        added_articles.update(articles)

        with open(category_chunk_dir.joinpath(f"{category}.category"), "wb") as f:
            article_names = [data.article_id_to_name[a] for a in articles]
            f.write(
                _serialize_category(
                    name, predecessors, successors, articles, article_names
                )
            )

    return added_articles


def _dir_list_content(path: pathlib.Path) -> bytes:
    acc = []
    for b in os.listdir(path):
        s = b.split(".")[0]
        if not s.isdigit():
            continue
        acc.append(int(s))
    return _bytes_from_uint32(acc)


def _write_dir_indices(config: RunConfig) -> None:
    config.dest.joinpath("dir_list.index").write_bytes(_dir_list_content(config.dest))
    for container in os.listdir(config.dest):
        container_path = config.dest.joinpath(container)
        if not container_path.is_dir():
            continue
        container_path.joinpath("dir_list.index").write_bytes(
            _dir_list_content(container_path)
        )
