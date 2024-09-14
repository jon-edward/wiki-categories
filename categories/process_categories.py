from array import array
from collections import defaultdict
import dataclasses
import datetime
import logging
import os
import pathlib
import shutil
from textwrap import dedent
from typing import Callable, Dict, DefaultDict, Iterable, List, Optional, Set, Tuple, Union

import networkx as nx

from parse import CategoryLink, Page


_UINT32_TYPECODE = "I"
_BALANCING_MOD_OPERAND = 2_000


def _to_uint32(val: Iterable[int]) -> bytes:
    return array(_UINT32_TYPECODE, val).tobytes()


def serialize_category(
        name: str,
        predecessors: Iterable[int],
        successors: Iterable[int],
        articles: Iterable[int]) -> bytes:

    name_bytes = name.encode()
    predecessors_bytes = _to_uint32(predecessors)
    successors_bytes = _to_uint32(successors)

    return (
        len(name_bytes).to_bytes(length=4) + name_bytes +
        len(predecessors_bytes).to_bytes(length=4) + predecessors_bytes +
        len(successors_bytes).to_bytes(length=4) + successors_bytes +
        _to_uint32(articles)
    )


@dataclasses.dataclass
class CategoriesInfo:
    categories_count: int
    articles_count: int
    finished: datetime.datetime

    def to_json(self) -> Dict[str, Union[str, int]]:
        return {
            "categoriesCount": self.categories_count,
            "articlesCount": self.articles_count,
            "finished": self.finished.strftime(r"%d/%m/%Y, %H:%M:%S")
        }


def process_categories(
        dest: pathlib.Path,
        category_links_gen: Callable[[], Iterable[CategoryLink]],
        pages_gen: Callable[[], Iterable[Page]],
        excluded_parents: Optional[Iterable[int]] = None,
        excluded_article_categories: Optional[Iterable[int]] = None,
        progress: bool = True) -> CategoriesInfo:

    if excluded_parents is None:
        excluded_parents = ()

    if excluded_article_categories is None:
        excluded_article_categories = ()

    articles_dir = dest.joinpath("articles")
    os.makedirs(articles_dir, exist_ok=True)

    id_to_name: Dict[int, str] = {}

    for page in pages_gen():
        id_to_name[page.page_id] = page.name

    name_to_id = {
        v: k for k, v in id_to_name.items()
    }

    category_edges: List[Tuple[int, int]] = []

    article_acc: DefaultDict[int, List[int]] = defaultdict(list)
    max_items = 100

    def push_article_list(category_id, _article_list, clear: bool = True):
        with articles_dir.joinpath(f"{category_id}.articles").open("ab") as f:
            f.write(b"".join(a.to_bytes(length=4) for a in _article_list))
        if clear:
            _article_list.clear()

    def append_id(category_id: int, article_id: int):
        _article_list = article_acc[category_id]
        _article_list.append(article_id)

        if len(_article_list) > max_items:
            push_article_list(category_id, _article_list)

    for category_link in category_links_gen():
        parent_id = name_to_id.get(category_link.parent_name, None)

        if parent_id is None:
            continue

        if category_link.is_article:
            append_id(parent_id, category_link.child_id)
        elif category_link.child_id in id_to_name:
            category_edges.append((parent_id, category_link.child_id))

    del name_to_id

    for k, article_list in article_acc.items():
        if not article_list:
            continue
        push_article_list(k, article_list, clear=False)

    del article_acc

    cat_graph = nx.DiGraph()
    cat_graph.add_edges_from(category_edges)

    def read_article_list(category_id: int) -> array[int]:
        try:
            return array(_UINT32_TYPECODE, articles_dir.joinpath(f"{category_id}.articles").read_bytes())
        except FileNotFoundError:
            return array(_UINT32_TYPECODE)

    excluded_categories = set()

    for e in excluded_parents:
        excluded_categories.update(cat_graph.successors(e))

    excluded_articles = set()

    for a in excluded_article_categories:
        excluded_articles.update(read_article_list(a))

    cat_graph.remove_nodes_from(excluded_categories)

    p_bar = None

    if excluded_articles or excluded_categories:
        logging.info(dedent(f"""
            Excluding {len(excluded_categories)} categories.
            Excluding {len(excluded_articles)} articles.
        """))

    if progress:
        from tqdm import tqdm

        p_bar = tqdm(total=len(cat_graph))
    
    added_articles: Set[int] = set()

    for category in cat_graph:

        name = id_to_name[category]
        predecessors = cat_graph.predecessors(category)
        successors = cat_graph.successors(category)

        category_chunk_dir = dest.joinpath(str(category % _BALANCING_MOD_OPERAND))
        category_chunk_dir.mkdir(exist_ok=True)

        articles = [a for a in read_article_list(category) if a not in excluded_articles]
        added_articles.update(articles)

        category_chunk_dir.joinpath(f"{category}.category").write_bytes(serialize_category(
            name,
            predecessors,
            successors,
            articles
        ))

        if p_bar is not None:
            p_bar.update(1)

    def dir_list_content(path: pathlib.Path) -> bytes:
        acc = []
        for b in os.listdir(path):
            s = b.split(".")[0]
            if not s.isdigit():
                continue
            acc.append(int(s))
        return _to_uint32(acc)

    dest.joinpath("dir_list.index").write_bytes(dir_list_content(dest))

    for container in os.listdir(dest):
        container_path = dest.joinpath(container)
        if not container_path.is_dir():
            continue
        container_path.joinpath("dir_list.index").write_bytes(dir_list_content(container_path))

    if p_bar is not None:
        p_bar.close()

    shutil.rmtree(articles_dir)

    return CategoriesInfo(
        categories_count=len(cat_graph),
        articles_count=len(added_articles),
        finished=datetime.datetime.now()
    )
