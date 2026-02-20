#!/usr/bin/env -S uv run
# /// script
# dependencies = ["httpx"]
# ///
import hashlib
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

import httpx

LFS_POINTER_VERSION = "version https://git-lfs.github.com/spec/v1"
LFS_OID_RE = re.compile(r"^oid sha256:([0-9a-f]{64})$")
LFS_SIZE_RE = re.compile(r"^size (\d+)$")


@dataclass(frozen=True)
class LfsPointer:
	path: Path
	oid: str
	size: int


def iter_files(root: Path) -> Iterator[Path]:
	for path in root.rglob("*"):
		if path.is_file():
			yield path


def parse_lfs_pointer(path: Path) -> LfsPointer | None:
	try:
		text = path.read_text(encoding="utf-8", errors="strict")
	except UnicodeDecodeError:
		return None

	lines = [line.strip() for line in text.splitlines() if line.strip()]
	if not lines or lines[0] != LFS_POINTER_VERSION:
		return None

	oid = None
	size = None
	for line in lines[1:]:
		oid_match = LFS_OID_RE.match(line)
		if oid_match:
			oid = oid_match.group(1)
			continue
		size_match = LFS_SIZE_RE.match(line)
		if size_match:
			size = int(size_match.group(1))
			continue

	if not oid or size is None:
		return None

	return LfsPointer(path=path, oid=oid, size=size)


def find_lfs_pointers(root: Path) -> List[LfsPointer]:
	pointers: List[LfsPointer] = []
	for path in iter_files(root):
		pointer = parse_lfs_pointer(path)
		if pointer:
			pointers.append(pointer)
	return pointers


def url_for_pointer(pointer: LfsPointer, base_url: str, root: Path) -> str:
	relative_path = pointer.path.relative_to(root).as_posix()
	return f"{base_url.rstrip('/')}/{relative_path}"


def download_to_temp(client: httpx.Client, url: str) -> Path:
	response = client.get(url, follow_redirects=True)
	response.raise_for_status()
	tmp_dir = tempfile.mkdtemp(prefix="fluxer-lfs-")
	tmp_path = Path(tmp_dir) / "download"
	with tmp_path.open("wb") as handle:
		for chunk in response.iter_bytes():
			handle.write(chunk)
	return tmp_path


def validate_download(path: Path, pointer: LfsPointer) -> Tuple[bool, str]:
	actual_size = path.stat().st_size
	if actual_size != pointer.size:
		return False, f"size mismatch (expected {pointer.size}, got {actual_size})"

	hasher = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			hasher.update(chunk)
	if hasher.hexdigest() != pointer.oid:
		return False, "sha256 mismatch"

	return True, "ok"


def overwrite_pointer(tmp_path: Path, target_path: Path) -> None:
	target_path.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(tmp_path, target_path)


def main(argv: List[str]) -> int:
	if len(argv) < 2:
		print("Usage: downloader.py <root> [base_url]", file=sys.stderr)
		return 2

	root = Path(argv[1]).resolve()
	base_url = argv[2] if len(argv) > 2 else "https://fluxerstatic.com"

	if not root.is_dir():
		print(f"Root not found: {root}", file=sys.stderr)
		return 2

	pointers = find_lfs_pointers(root)
	if not pointers:
		print("No LFS pointer files found.")
		return 0

	print(f"Found {len(pointers)} LFS pointer files under {root}.")
	download_map = {pointer.path: url_for_pointer(pointer, base_url, root) for pointer in pointers}

	with httpx.Client(timeout=60.0) as client:
		for pointer in pointers:
			url = download_map[pointer.path]
			print(f"Downloading {url}")
			try:
				tmp_path = download_to_temp(client, url)
			except Exception as exc:
				print(f"Failed to download {url}: {exc}", file=sys.stderr)
				continue

			try:
				ok, reason = validate_download(tmp_path, pointer)
				if not ok:
					print(f"Validation failed for {pointer.path}: {reason}", file=sys.stderr)
					continue

				overwrite_pointer(tmp_path, pointer.path)
				print(f"Replaced {pointer.path}")
			finally:
				shutil.rmtree(tmp_path.parent, ignore_errors=True)

	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
