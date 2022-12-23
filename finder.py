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


def list_files(folder: Path) -> List[Path]:
    root.info(f"Getting list of files from {folder}. It may take a while...")
    result = []
    for path in folder.rglob("*"):
        if path.is_file():
            root.debug(f"Added to file list: {path}")
            result.append(path)
    return result


def main() -> None:
    root.info("Starting...")

    # Parse args
    parser = ArgumentParser()
    parser.add_argument("folder", help="Directory to search duplicates in (recursively)")
    parser.add_argument("-a", "--action", help="Action to perform when duplicates are found.",
                        choices=["delete", "list", "file", "move"], default="list")

    args = parser.parse_args()

    # Retrieve list of files
    files = list_files(Path(args.folder))
    root.info(f"Collected {len(files)} files")

    # Get duplicates
    duplicates = get_duplicates(files)
    root.info(f"{duplicates}")

    # Action
    action = args.action.lower()

    if action in ("d", "delete"):
        # Delete duplicates leaving only one file behind
        for v in duplicates.values():
            for f in v[1:]:  # Leave one of the files untouched
                f.unlink(True)
    elif action in ("m", "move"):
        # Move duplicated files into "duplicates" folder
        output_folder = Path(args.folder).joinpath("duplicates")
        os.mkdir(output_folder)
        for hash_str, files in duplicates.items():
            subfolder = output_folder.joinpath(hash_str)
            os.mkdir(subfolder)
            for file in files:
                shutil.move(str(file), str(subfolder))
    elif action in ("f", "file"):
        # List files in result.txt
        with open("results.txt", "w") as output:
            for hash_str, files in duplicates.items():
                print(f"{hash_str}:", file=output)
                for file in files:
                    print(f"\t{file}", file=output)
    else:
        # List files in stdout
        for hash_str, files in duplicates.items():
            root.info(f"{hash_str}:")
            for file in files:
                root.info(f"\t{file}")

    root.info("All done!")


if __name__ == '__main__':
    main()
