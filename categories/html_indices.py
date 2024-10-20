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


def generate_indices(path: pathlib.Path, root_path=pathlib.Path("/wiki-categories/")):
    """
    Generate an index.html file at each subdirectory and root of path directory that lists
    files for navigation.
    """
    for subdir, dirs, files in os.walk(path):
        with open(
            pathlib.Path(subdir, "index.html"),
            "wb",
        ) as f:
            index = bs4.BeautifulSoup(INDEX_HTML, "html.parser")

            sub_index = index.find(id="sub-index")

            def format_dir(relative_d: pathlib.Path) -> str:
                return f"/{relative_d}/" if str(relative_d) != "." else "root"

            def create_sub_path_entry(
                sub_path: pathlib.Path, display_text: str = None, is_dir: bool = False
            ):
                p = root_path.joinpath(sub_path.relative_to(path))

                li_tag = index.new_tag("li")
                li_tag.attrs["class"] = "is-dir" if is_dir else "is-file"
                a_tag = index.new_tag("a")

                href_content = str(p)

                a_tag.attrs["href"] = href_content + (
                    "/" if is_dir and href_content != "/" else ""
                )

                if display_text is None:
                    a_tag.append(p.name + ("/" if is_dir else ""))
                else:
                    a_tag.append(display_text)

                li_tag.append(a_tag)

                return li_tag

            relative_path = format_dir(pathlib.Path(subdir).relative_to(path))

            index.find(id="sub-path").append(f"Directory listing for {relative_path}:")

            try:
                head_entry = create_sub_path_entry(
                    pathlib.Path(subdir).parent, display_text="..", is_dir=True
                )
                head_entry.attrs["class"] += " is-head-dir"
                sub_index.append(head_entry)
            except ValueError:
                pass

            max_name_len = max(
                len(x.split(".")[0]) for x in itertools.chain(files, dirs)
            )

            def int_if_digits(path_segment: str):
                name, *_ = path_segment.split(".")
                if name.isdigit():
                    return f"{'0'*(max_name_len-len(name))}{name}"
                return name.lower()

            dirs.sort(key=int_if_digits)

            for dir_ in dirs:
                sub_index.append(
                    create_sub_path_entry(pathlib.Path(subdir, dir_), is_dir=True)
                )

            files.sort(key=int_if_digits)

            for file in files:
                if file == "index.html":
                    continue

                sub_index.append(create_sub_path_entry(pathlib.Path(subdir, file)))

            f.write(index.prettify(encoding="utf-8"))


if __name__ == "__main__":
    # For debugging. Add files to /pages to test index creation.
    # This sets the root path to the base of the directory, where in production
    # this will be set to the GH Pages repo name.
    generate_indices(
        pathlib.Path(__file__).parent.parent.joinpath("pages"),
        root_path=pathlib.Path("/"),
    )
