# Duplicate finder script
Simple script to find and process duplicated files in a given folder.

# Usage
Run `finder.py` with two positional arguments:
* `action`: what to do with found duplicates,
* `folder`: folder where to look for duplicates.

Example command:
```commandline
python3 list /home/anon 
```

## Available actions
There are several ways to handle duplicates:
* `list`: prints list of duplicates grouped by their hashes (see below) into console.
* `file`: same as above, but output is saved in `results.txt` file in current working directory.
* `move`: creates sub-folder in the `folder` and moves all duplicated files there.
* `delete`: removes duplicated files (leaving one copy behind, of course).

# How it works
Script recursively collects paths to all files in a given folder.

Then for each file it calculates MD5 hash of first 4096 bytes.
This significantly reduces disk load and time required for analysis.

After that script looks through this collection of "partial hashes".
If two or more files have the same "partial hash", then files read in full and hash for the whole file is calculated.

Finally, if there are any files present that have the same full hash, they are considered duplicates
and chosen `action` is applied to them.
