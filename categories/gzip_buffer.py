import pathlib
from typing import Iterable
import zlib

import requests
from tqdm import tqdm


def read_buffered_gzip_remote(url: str, chunk_size: int = 1024, progress: bool = True) -> Iterable[bytes]:
    response = requests.get(url, stream=True)

    stream = response.iter_content(chunk_size=chunk_size)
    dc_obj = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)

    stream_len = int(response.headers.get("Content-Length", -1))

    p_bar = None

    if stream_len != -1 and progress:
        p_bar = tqdm(total=stream_len, unit='B', unit_scale=True, unit_divisor=1024)

    for chunk in stream:
        yield dc_obj.decompress(chunk)
        if p_bar is not None:
            p_bar.update(len(chunk))

    if p_bar is not None:
        p_bar.close()


def read_buffered_gzip_local(path: pathlib.Path, chunk_size: int = 1024, progress: bool = True) -> Iterable[bytes]:
    dc_obj = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)

    p_bar = None

    if progress:
        p_bar = tqdm(total=path.lstat().st_size, unit='B', unit_scale=True, unit_divisor=1024)

    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            yield dc_obj.decompress(chunk)
            if p_bar is not None:
                p_bar.update(len(chunk))

    if p_bar is not None:
        p_bar.close()
