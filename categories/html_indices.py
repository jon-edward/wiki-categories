import os
import pathlib
import re
import textwrap


with open(os.path.join(os.path.dirname(__file__), "category_parsing.js")) as f:
    _CATEGORY_PARSING_SCRIPT = f.read()


def _index_start_template(rel_dir: str) -> str:
    """
    Generate the HTML template for the index page.
    """
    return textwrap.dedent(f"""
    <!DOCTYPE html>
    <html>
        <head><meta charset="utf-8"><title>Index of {rel_dir}</title>
            <style>
                body {{ background: #202124; color: #d3d3d3; font-family: monospace, monospace; }}
                h1 {{ color: #e0b97d; }}
                table {{ border-collapse: collapse; width: 100%; max-width: 700px; }}
                th, td {{ padding: 0.25em 0.75em; text-align: left; }}
                th {{ color: #b0b0b0; font-weight: normal; border-bottom: 1px solid #333; }}
                tr {{ border-bottom: 1px solid #232323; }}
                a {{ color: #7ec3d9; text-decoration: none; }}
                a.dir {{ color: #7ebf8e; font-weight: bold; }}
                a:hover {{ text-decoration: underline; }}
                td.size {{ color: #888; font-size: 0.95em; width: 7em; white-space: nowrap; }}
            </style>
        </head>
    <body>
        <script>
        {_CATEGORY_PARSING_SCRIPT}
        </script>
        <h1>Index of {rel_dir}</h1>
        <table>
            <thead><tr><th>Name</th><th>Size</th></tr></thead>
            <tbody>
    """)


def index_directories(base_path: pathlib.Path, site_root: str = ""):
    def human_size(num):
        for unit in ["B", "K", "M", "G", "T", "P"]:
            if abs(num) < 1024.0:
                if unit == "B":  # Special case for bytes to avoid decimal point
                    return f"{num:3.0f}{unit}"
                return f"{num:3.1f}{unit}"
            num /= 1024.0
        return f"{num:.1f}E"

    """
    Recursively create an index.html file in every directory under base_path.
    Each index.html lists the contents of the directory with links.
    """

    def natural_key(s: str) -> list[int | str]:
        """
        Convert a string to a list of integers and strings for natural sorting.
        This allows sorting numbers in the string naturally (e.g., 'file10' after 'file2').
        """
        s_clean = s[:-1] if s.endswith("/") else s
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\\d+)", s_clean)
        ]

    for root, dirs, files in os.walk(base_path):
        # Exclude index.html from the list
        dir_entries = sorted([d + "/" for d in dirs], key=natural_key)
        file_entries = sorted([f for f in files if f != "index.html"], key=natural_key)
        entries = dir_entries + file_entries
        rel_dir = os.path.relpath(root, base_path)
        # Ensure site_root starts and ends with a single slash if not empty
        site_root_clean = ("/" + site_root.strip("/") + "/") if site_root else "/"
        # Compute the URL path for this directory
        url_dir = site_root_clean + (rel_dir + "/" if rel_dir != "." else "")
        content = _index_start_template(rel_dir)

        # Add parent directory link if not at base
        if os.path.abspath(root) != os.path.abspath(base_path):
            content += '<tr><td><a href="../" class="dir">../</a></td><td class="size"></td></tr>'

        for entry in entries:
            href = url_dir + entry
            is_dir = entry.endswith("/")
            cls = ' class="dir"' if is_dir else ""
            size_str = ""
            if is_dir:
                dir_path = os.path.join(root, entry[:-1])
                try:
                    subdirs = [
                        d
                        for d in os.listdir(dir_path)
                        if os.path.isdir(os.path.join(dir_path, d))
                    ]
                    files_ = [
                        f
                        for f in os.listdir(dir_path)
                        if os.path.isfile(os.path.join(dir_path, f))
                        and f != "index.html"
                    ]
                    size_str = f"{len(subdirs)} dirs, {len(files_)} files"
                except Exception:
                    size_str = ""
                content += f'<tr><td><a href="{href}"{cls}>{entry}</a></td><td class="size">{size_str}</td></tr>'
            else:
                file_path = os.path.join(root, entry)
                try:
                    size = os.path.getsize(file_path)
                    size_str = human_size(size)
                except OSError:
                    pass
                # Use the filename (without extension) as the categoryId for showCategory
                category_id, extension = os.path.splitext(entry)
                if extension.lower() == ".category":
                    content += f'<tr><td><a href="#" onclick="showCategory(\'{category_id}\');return false;">{entry}</a></td><td class="size">{size_str}</td></tr>'
                else:
                    content += f'<tr><td><a href="{href}">{entry}</a></td><td class="size">{size_str}</td></tr>'

        content += "</tbody></table></body></html>"

        index_path = os.path.join(root, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    # Example usage
    base_path = pathlib.Path("pages")  # Change to your desired base path
    index_directories(base_path, "wiki-categories")
    print(f"Index files created under {base_path.resolve()}")
