import argparse

from categories.config import RunConfig
from categories.cli import main

# EXCLUDED PARENTS:
# 44084293 - Wikipedia template categories
# 869270 - Stub categories
# 24611576 - Noindexed pages
# 24500262 - All redirect categories
# 23302197 - Disambiguation categories
# 24585745 - Wikipedia soft redirected categories
# 30176254 - Container categories
# 15961454 - Hidden categories
# 7361045 - Tracking categories
# 3746758 - Wikipedians by WikiProject

# EXCLUDED GRANDPARENTS:
# 6256963 - Articles by importance
# 6256931 - Articles by quality

# EXCLUDED ARTICLE CATEGORIES:
# 43077354 - All stub articles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    config = RunConfig(
        excluded_parents=[
            44084293,
            869270,
            24611576,
            24500262,
            23302197,
            24585745,
            30176254,
            15961454,
            7361045,
            3746758
        ],
        excluded_grandparents=[6256963, 6256931],
        excluded_article_categories=[43077354],
        dev=args.dev,
        use_cache=args.dev,
        clean=args.dev,
    )

    if not args.dev:
        config.index_root_path = "/wiki-categories/"

    main(config)
