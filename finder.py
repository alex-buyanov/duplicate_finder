import hashlib
import logging
import os
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Dict

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


def get_hash(path: Path, full_scan=False) -> str:
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

    # Collect all files from hashes with more than one file
    possible_duplicates = []
    for file_list in partial_hashes.values():
        if len(file_list) > 1:
            possible_duplicates.extend(file_list)

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
        root.info(f"{hash_str}:")
        for file in files:
            root.info(f"\t{file}")


def output_to_file(duplicates: Dict[str, List[Path]]) -> None:
    with open("results.txt", "w") as output:
        for hash_str, files in duplicates.items():
            print(f"{hash_str}:", file=output)
            for file in files:
                print(f"\t{file}", file=output)


def move_duplicates(duplicates: Dict[str, List[Path]], output_folder: Path) -> None:
    os.mkdir(output_folder)
    for hash_str, files in duplicates.items():
        subfolder = output_folder.joinpath(hash_str)
        os.mkdir(subfolder)
        for file in files:
            shutil.move(str(file), str(subfolder))


def delete_duplicates(duplicates: Dict[str, List[Path]]) -> None:
    for v in duplicates.values():
        for f in v[1:]:  # Leave one of the files untouched
            f.unlink(True)


def main() -> None:
    root.info("Starting...")

    # Parse args
    parser = ArgumentParser()
    parser.add_argument("action", help="Action to perform when duplicates are found",
                        choices=["delete", "list", "file", "move"])
    parser.add_argument("folder", help="Directory to recursively search duplicates in")

    args = parser.parse_args()
    action, folder = args.action, Path(args.folder)

    # Retrieve list of files
    root.info(f"Getting list of files from {folder}. It may take a while...")
    files = [f for f in folder.rglob("*") if f.is_file()]
    root.info(f"Collected {len(files)} files")

    # Get duplicates
    root.info("Hashing collected files in search of duplicates. This will take even more time...")
    duplicates = get_duplicates(files)
    if (duplicates):
        root.info(f"Found {len(duplicates)} duplicated files")
    else:
        root.info(f"No duplicates were found. Have a nice day.")

    # Action
    if action == "delete":
        delete_duplicates(duplicates)
    elif action == "move":
        move_duplicates(duplicates, Path(args.folder).joinpath("duplicates"))
    elif action == "file":
        output_to_file(duplicates)
    else:
        output_to_stdout(duplicates)

    root.info("All done.")


if __name__ == '__main__':
    main()
