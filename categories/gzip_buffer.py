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
    If the path is a remote url, it streams the file over the network.
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

    response = _get_remote_response(url)
    stream = response.iter_content(chunk_size=chunk_size)
    dc_obj = _get_gzip_decompressor()
    stream_len = _get_stream_length(response)
    p_bar = _create_progress_bar(stream_len, progress)
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

    dc_obj = _get_local_decompressor(path)
    p_bar = _create_progress_bar(path.lstat().st_size, progress)
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            yield dc_obj.decompress(chunk)
            p_bar.update(len(chunk))
    p_bar.close()


def _get_remote_response(url: str) -> requests.Response:
    return requests.get(url, stream=True, timeout=10)


def _get_gzip_decompressor():
    return zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)


def _get_stream_length(response: requests.Response) -> int:
    return int(response.headers.get("Content-Length", -1))


def _create_progress_bar(total: int, progress: bool) -> tqdm:
    return tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        disable=not progress,
        miniters=1_000_000,
    )


def _get_local_decompressor(
    path: pathlib.Path,
):
    if not path.suffix == ".gz":
        return _IdentityDecompressor()
    return zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)
