#!/usr/bin/env python3

import shutil
import re
import os
import glob
from pathlib import Path
import traceback
from sipr0n import util
from sipr0n import env



def run(chipid=None, vendor=None, user=None, dry=True):
    env.setup_env_default()

    page_fn = env.WWW_DIR + f"/archive/data/pages/{user}/{vendor}/{chipid}.txt"
    print(f"rm -f {page_fn}")
    print("  Exists: ", os.path.exists(page_fn))
    if os.path.exists(page_fn) and not dry:
        os.unlink(page_fn)

    # for now assume that only this user has files there
    # also we don't want to destroy a specific variant
    map_dir = env.WWW_DIR + f"/map/{vendor}/{chipid}"
    print(f"rm -rf {map_dir}")
    # Check if anything not from this user
    if os.path.exists(map_dir):
        files = os.listdir(map_dir)
        for map_fn in files:
            if map_fn == "single":
                single_dir = map_dir + "/single"
                single_files = os.listdir(single_dir)
                for fn in single_files:
                    print(f"  rm single/{fn}")
                    assert user in fn, f"Unexpected asset not from user: {fn}" 
            elif ".manifest" in map_fn:
                a_map = map_dir + "/" + map_fn
                print(f"  rm -rf {a_map}")
            else:
                a_map = map_dir + "/" + map_fn
                print(f"  rm -rf {a_map}")
                assert os.path.isdir(a_map), a_map
                assert user in map_fn, f"Unexpected asset not from user: {map_fn}" 

    if os.path.exists(map_dir) and not dry:
        shutil.rmtree(map_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Delete a page / map file, usually to re-upload")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--chipid", required=True)
    parser.add_argument("--user", required=True)
    args = parser.parse_args()
    run(vendor=args.vendor, chipid=args.chipid, user=args.user, dry=args.dry)


if __name__ == "__main__":
    main()
