import itertools
import os
import pathlib

import bs4

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <style>
    :root {
      background-color:#fff;
      color:#333;
      font-family:system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Oxygen,Ubuntu,Cantarell,Open Sans,Helvetica Neue,sans-serif;
      font-size:medium
    }
    .dark-variant {
      display:none
    }
    li {
      margin:5px 0;
      font-family: monospace;
    }
    ul {
      list-style-type: none;
    }
    
    @media (prefers-color-scheme: dark) {
      :root {
        background-color:#333;
        color:#fff
      }
      a {
        color:#7568ff
      }
      a:visited {
        color:#f98fff
      }
    }
    </style>
    <title>wiki-categories</title>
  </head>
  <body>
    <main>
        <h1>wiki-categories</h1>
        <p>This is the index for the wiki-categories site. See the 
        <a href="https://github.com/jon-edward/wiki-categories">GitHub repo</a> for its usage, file formats, 
        and creation.</p>
        <b id="sub-path"></b>
        <ul id="sub-index">
        </ul>
    </main>
  </body>
</html>
"""


def generate_indices(path: pathlib.Path, root_path: str) -> None:
    """
    Generate an index.html file at each subdirectory and root of path directory that lists files for navigation.
    """
    for subdir, dirs, files in os.walk(path):
        _write_index_html(subdir, dirs, files, path, root_path)


def _write_index_html(
    subdir: str, dirs: list[str], files: list[str], path: pathlib.Path, root_path: str
) -> None:
    with open(pathlib.Path(subdir, "index.html"), "w", encoding="utf-8") as f:
        index = bs4.BeautifulSoup(INDEX_HTML, "html.parser")
        sub_index = _get_sub_index_tag(index)

        relative_path = _format_dir(pathlib.Path(subdir).relative_to(path))
        sub_index.append(f"Directory listing for {relative_path}:")

        _add_head_entry(sub_index, index, subdir, path, root_path)

        max_name_len = _get_max_name_len(files, dirs)

        dirs.sort(key=lambda x: _int_if_digits(x, max_name_len))

        for dir_ in dirs:
            sub_index.append(
                _create_sub_path_entry(
                    index, pathlib.Path(subdir, dir_), path, root_path, is_dir=True
                )
            )

        files.sort(key=lambda x: _int_if_digits(x, max_name_len))

        for file in files:
            if file == "index.html":
                continue
            sub_index.append(
                _create_sub_path_entry(
                    index, pathlib.Path(subdir, file), path, root_path, is_dir=False
                )
            )

        content: str = index.prettify(encoding="utf-8")  # type: ignore[return-value]

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        f.write(content)


def _get_sub_index_tag(index: bs4.BeautifulSoup) -> bs4.element.Tag:
    sub_index = index.find(id="sub-index")
    if not isinstance(sub_index, bs4.element.Tag):
        raise ValueError("Index HTML template is missing the 'sub-index' element.")
    return sub_index


def _format_dir(relative_d: pathlib.Path) -> str:
    return f"/{relative_d}/" if str(relative_d) != "." else "root"


def _add_head_entry(
    sub_index: bs4.element.Tag,
    index: bs4.BeautifulSoup,
    subdir: str,
    path: pathlib.Path,
    root_path: str,
) -> None:
    try:
        head_entry = _create_sub_path_entry(
            index,
            pathlib.Path(subdir).parent,
            path,
            root_path,
            display_text="..",
            is_dir=True,
        )
        head_entry.attrs["class"] += " is-head-dir"
        sub_index.append(head_entry)
    except ValueError:
        pass


def _get_max_name_len(files: list[str], dirs: list[str]) -> int:
    return (
        max(len(x.split(".")[0]) for x in itertools.chain(files, dirs))
        if files or dirs
        else 0
    )


def _int_if_digits(path_segment: str, max_name_len: int) -> str:
    name, *_ = path_segment.split(".")
    if name.isdigit():
        return f"{'0'*(max_name_len-len(name))}{name}"
    return name.lower()


def _create_sub_path_entry(
    index: bs4.BeautifulSoup,
    sub_path: pathlib.Path,
    path: pathlib.Path,
    root_path: str,
    display_text: str | None = None,
    is_dir: bool = False,
) -> bs4.element.Tag:
    href_content = os.path.join(root_path, sub_path.relative_to(path))

    li_tag = index.new_tag("li")
    li_tag.attrs["class"] = "is-dir" if is_dir else "is-file"

    a_tag = index.new_tag("a")
    a_tag.attrs["href"] = href_content + (
        os.path.sep if is_dir and href_content != os.path.sep else ""
    )

    if display_text is None:
        a_tag.append(href_content + (os.path.sep if is_dir else ""))
    else:
        a_tag.append(display_text)

    li_tag.append(a_tag)
    return li_tag


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate HTML indices for directories.")
    parser.add_argument("path", type=pathlib.Path, help="Path to the directory to index.")
    parser.add_argument(
        "--root-path",
        type=str,
        default=os.path.sep,
        help="Root path for the HTML indices.",
    )
    args = parser.parse_args()

    generate_indices(args.path, args.root_path)
