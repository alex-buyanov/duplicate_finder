import hashlib
import logging
import os
import shutil
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Logger setup
log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)


def get_hash(path: Path, full_scan=False) -> str:
    log.debug(f"Hashing file ({'full' if full_scan else 'first 4096 bytes'}): {path}")
    with path.open("rb") as f:
        if full_scan:
            md5_value = hashlib.md5()
            data = f.read(4096)
            while data:
                md5_value.update(data)
                data = f.read(4096)
            return md5_value.hexdigest()
        else:
            return hashlib.md5(f.read(4096)).hexdigest()


def get_duplicates(files: List[Path]) -> Dict[str, List[Path]]:
    # Read partial hashes
    partial_hashes = dict()
    for file in files:
        file_hash = get_hash(file)
        if file_hash not in partial_hashes:
            partial_hashes[file_hash] = [file]
        else:
            partial_hashes[file_hash].append(file)

    log.info("Partial hashes collected.")

    # Collect all files from hashes with more than one file
    possible_duplicates = []
    for file_list in partial_hashes.values():
        if len(file_list) > 1:
            possible_duplicates.extend(file_list)

    if not possible_duplicates:
        return dict()
    else:
        log.info(f"Running thorough analysis on {len(possible_duplicates)} files...")

    # On every file run full hash
    definite_duplicates = dict()
    for file in possible_duplicates:
        file_hash = get_hash(file, True)
        if file_hash not in definite_duplicates:
            definite_duplicates[file_hash] = [file]
        else:
            definite_duplicates[file_hash].append(file)

    # Filter out unique hashes and return result
    definite_duplicates = {k: v for k, v in definite_duplicates.items() if len(v) > 1}
    return definite_duplicates


def output_to_stdout(duplicates: Dict[str, List[Path]]) -> None:
    for hash_str, files in duplicates.items():
        log.info(f"{hash_str}:")
        for file in files:
            log.info(f"\t{file}")


def output_to_file(duplicates: Dict[str, List[Path]]) -> None:
    results = Path("results.txt").absolute()
    with results.open("w") as output:
        for hash_str, files in duplicates.items():
            print(f"{hash_str}:", file=output)
            for file in files:
                print(f"\t{file}", file=output)
    log.info(f"Results were saved in {results}")


def move_duplicates(duplicates: Dict[str, List[Path]], output_folder: Path) -> None:
    log.info(f"Moving all duplicated files into {output_folder}...")
    os.mkdir(output_folder)
    count_bytes, count_files = 0, 0
    for hash_str, files in duplicates.items():
        subfolder = output_folder.joinpath(hash_str)
        os.mkdir(subfolder)
        for file in files:
            try:
                size = file.stat().st_size
                shutil.move(str(file), str(subfolder))
                count_bytes += size
                count_files += 1
            except OSError as e:
                log.warning(f"Failed to move {file}: {e}")
    log.info(
        f"Moved {count_bytes // 1024 ** 2} MB in {count_files} files to {output_folder}. Now, sort them out by hand.")


def delete_duplicates(duplicates: Dict[str, List[Path]]) -> None:
    log.info("Deleting duplicates. That'll be quick...")
    count_bytes = 0
    for v in duplicates.values():
        for f in v[1:]:  # Leave one of the files untouched
            try:
                size = f.stat().st_size
                f.unlink()
                count_bytes += size  # Put here and not above to not skew counter if unlink() raises error
                log.debug(f"Deleted {f}")
            except OSError as e:
                log.warning(f"Failed to delete {f}: {e}")
    log.info(f"Deleted {count_bytes // 1024 ** 2} MB. Enjoy some free space.")


def main() -> None:
    # Parse args
    parser = ArgumentParser()
    parser.add_argument("action", help="Action to perform when duplicates are found",
                        choices=["delete", "list", "file", "move"])
    parser.add_argument("folder", help="Directory to recursively search duplicates in")

    args = parser.parse_args()
    action, folder = args.action, Path(args.folder)

    # Retrieve list of files
    log.info(f"Getting list of files from {folder}. It may take a while...")
    files = [f for f in folder.rglob("*") if f.is_file()]
    log.info(f"Collected {len(files)} files")

    if not files:
        log.info("Nothing to do here. Bye!")
        return

    # Get duplicates
    log.info("Hashing collected files in search of duplicates. This will take even more time...")
    duplicates = get_duplicates(files)
    if duplicates:
        log.info(f"Found {len(duplicates)} duplicated file content.")
    else:
        log.info(f"No duplicates were found. Have a nice day.")

    # Action
    if action == "delete":
        delete_duplicates(duplicates)
    elif action == "move":
        move_duplicates(duplicates, Path(args.folder).joinpath(datetime.now().strftime("%Y-%m-%d_%H%M%S")))
    elif action == "file":
        output_to_file(duplicates)
    else:
        output_to_stdout(duplicates)

    log.info("All done.")


if __name__ == '__main__':
    main()
