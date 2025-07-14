"""
Defines the configuration for the categories processing script.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Sequence

import argparse_dataclass

@dataclass
class RunConfig:
    language: str = "en"
    dest: Path = Path("pages")
    index_root_path: str = field(default=os.path.sep, metadata={"help": "Root path for HTML indices."})
    excluded_parents: list[int] = field(default_factory=list, metadata={"nargs": "*"})
    excluded_grandparents: list[int] = field(default_factory=list, metadata={"nargs": "*"})
    excluded_article_categories: list[int] = field(default_factory=list, metadata={"nargs": "*"})
    max_articles_per_category: int = field(default=1000, metadata={"help": "Maximum number of articles per category. Set to -1 for no limit."})
    dev: bool = field(default=False, metadata={"help": "Enable development mode with additional logging and progress bars."})
    clean: bool = field(default=False, metadata={"help": "Clean the destination directory before processing."})
    use_cache: bool = field(default=False, metadata={"help": "Use cached data instead of downloading dumps if available."})
    no_indices: bool = field(default=False, metadata={"help": "Do not generate HTML indices."})
    balancing_mod_operand: int = field(default=2000, metadata={"help": "Modulus for balancing categories into bins."})
    safe_depth: int = field(default=15, metadata={"help": "Depth from root node that should not be deleted from by article count percentile."})
    article_count_percentile: int = field(default=30, metadata={"help": "Percentile of article count that a category must have to not be deleted."})
    root_node: int = field(default=14105005, metadata={"help": "Root node ID for the category graph. In English Wikipedia, this is the ID for 'Category:Contents'."})

def parse_config(args: Sequence[str] | None = None) -> RunConfig:
    parser = argparse_dataclass.ArgumentParser(RunConfig)
    return parser.parse_args(args)


if __name__ == "__main__":
    config = parse_config()
    print(config)
