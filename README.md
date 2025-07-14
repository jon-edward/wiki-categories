# wiki-categories

This contains tools for constructing the category tree for a
given Wikipedia language.

## Usage

```shell
python3 categories --language en --dest ./public/categories
```

The above command serializes the category tree for the
English Wikipedia, and stores it in the `./public/categories`
directory. See `python3 categories --help` for available
options.

## Format

The category tree is split into bins, in which `.category`
files are placed. Directories are named as the remainder of
a given category's id divided by 2000. This balancing was
chosen by observation of the English Wikipedia, which at the
time of writing has about 2 million unique categories.

A `.category` file is a concatenation of fields, each field starts
with a 32-bit integer that describes how long the value is in bytes,
and is immediately followed by the value. The file is named by its page
id.

The fields of the binary file are as follows (in this order):

1. name - A utf8-encoded name of the category.
2. predecessors - An array of unsigned 32-bit integers which lists the ids of categories having this category
   as a successor.
3. successors - An array of unsigned 32-bit integers which lists the ids of categories immediately following this
   category in the hierarchy. For example, the "Climate activists" category is a successor of "Climate".
4. articles - An array of unsigned 32-bit integers which lists the ids of this category's articles.
5. article_names - An array of utf8-encoded strings which lists the names of this category's articles, null-terminated.

The `.category` format can be easily deserialized using the following script:

```py
from dataclasses import dataclass
import struct


@dataclass
class Category:
  name: str
  predecessors: list[int]
  successors: list[int]
  articles: list[int]
  article_names: list[str]


def uint32_from_bytes(data: bytes) -> list[int]:
  num_integers = len(data) // 4
  return list(struct.unpack(f'>{num_integers}I', data))

def str_list_from_bytes(data: bytes) -> list[str]:
  return [s.decode("utf-8") for s in data.split(b"\0")]

def deserialize(category_bytes: bytes) -> Category:
  pos = 0

  def read(x: int) -> bytes:
    nonlocal pos
    output = category_bytes[pos:pos+x]
    pos += x
    return output

  def read_field() -> bytes:
    value_len = int.from_bytes(read(4), "big")
    return read(value_len)

  return Category(
    read_field().decode("utf-8"),
    uint32_from_bytes(read_field()),
    uint32_from_bytes(read_field()),
    uint32_from_bytes(read_field()),
    str_list_from_bytes(read_field()),
  )
```

The script generates a `.index` file in the root directory and
each of its bins - this should be interpreted as an array
of unsigned 32-bit integers. This array describes the names of
the bins (in the case of the root directory), and the ids of
the categories contained within the bin (in the case of a
category bin).

The script generates a `run_info.json` file in the output directory root.
This is used for checking if the external assets have changed
since the last run, and provides basic information about the
run output.

The motivation of separating the large number of category
files into bins serves two major purposes - to allow the user
to find a random category without downloading an entire
category id index and to ease reading the directory
contents during development.
