#!/bin/bash
# This script runs the categories processing for the English Wikipedia.

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

if [[ $* == *--dev* ]]; then
  # If the --dev flag is present, we run with additional arguments for development.
  extra_args=(--dev --use-cache --clean)
else
  extra_args=(--index-root-path "/wiki-categories/")
fi

python ./categories --language en \
    --excluded-parents \
        44084293 \
        869270 \
        24611576 \
        24500262 \
        23302197 \
        24585745 \
        30176254 \
        15961454 \
        7361045 \
        3746758
    --excluded-article-categories \
        43077354 \
    --excluded-grandparents \
        6256963 \
        6256931 \
    ${extra_args[@]}
