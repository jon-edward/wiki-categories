"""
Contains utilities to iterate over a remote or local gzip-compressed file.
"""

import pathlib
from typing import Iterable
import zlib

import requests
from tqdm import tqdm


def read_buffered_gzip(
    path_or_url: pathlib.Path | str, chunk_size: int = 1024, progress: bool = True
) -> Iterable[bytes]:
    """
    Read chunks of a gzipped file, either local or remote.
    If the path is a local file, it reads from the file system.
    If the path is a remote url, it downloads the file and reads it.
    """
    if isinstance(path_or_url, pathlib.Path):
        return read_buffered_gzip_local(path_or_url, chunk_size, progress)
    return read_buffered_gzip_remote(path_or_url, chunk_size, progress)


def read_buffered_gzip_remote(
    url: str, chunk_size: int = 1024, progress: bool = True
) -> Iterable[bytes]:
    """
    Read chunks of a gzipped remote asset by url.
    """

    response = requests.get(url, stream=True, timeout=10)

    stream = response.iter_content(chunk_size=chunk_size)
    dc_obj = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)

    stream_len = int(response.headers.get("Content-Length", -1))

    p_bar = tqdm(total=stream_len, unit="B", unit_scale=True, unit_divisor=1024, disable=not progress)

    for chunk in stream:
        yield dc_obj.decompress(chunk)
        p_bar.update(len(chunk))
    
    p_bar.close()

class _IdentityDecompressor:
    """
    A decompressor that does not decompress data.
    """
    def decompress(self, data: bytes) -> bytes:
        return data

def read_buffered_gzip_local(
    path: pathlib.Path, chunk_size: int = 1024, progress: bool = True
) -> Iterable[bytes]:
    """
    Read chunks of a gzipped local asset by path.
    """

    if not path.suffix == ".gz":
        # Not a gzipped file, return the data as is
        dc_obj = _IdentityDecompressor()
    else:
        dc_obj = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)

    p_bar = tqdm(
        total=path.lstat().st_size, unit="B", unit_scale=True, unit_divisor=1024, disable=not progress
    )

    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            yield dc_obj.decompress(chunk)
            p_bar.update(len(chunk))

    p_bar.close()
