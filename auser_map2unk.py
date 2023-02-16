#!/usr/bin/env python3
"""
Seed new scheme by marking all assets with an unknown collection
Also create baseline metadata noting file types
"""

import shutil
import re
import os
import glob
from pathlib import Path
import traceback
from sipr0n import util
from sipr0n import simap
import glob
from sipr0n import env


def single_fn_add_user(fn, collection):
    vendor, chipid, flavor, ext = util.parse_map_image_vcfe(fn)
    return util.map_image_uvcfe_to_basename(vendor, chipid, collection, flavor,
                                            ext)


"""
Changes:
-Prefix map dirs with user
-Convert single to have unknown user
-Add manifest

After this run auser_map_adduser
Maybe some sort of consistency checker after
"""


def run(mapdir, dry=False, ignore_errors=False):
    env.setup_env_default()

    mapdir = env.MAP_DIR
    new_collection = "unknown"
    assert "www/map" in mapdir
    assert os.path.basename(mapdir) == "map"
    for vendor_dir in sorted(os.listdir(mapdir)):
        vendor_dir = os.path.join(mapdir, vendor_dir)
        for chipid_dir in sorted(os.listdir(vendor_dir)):
            print("Check", chipid_dir)
            chipid_dir = os.path.join(vendor_dir, chipid_dir)
            mfn = chipid_dir + "/.manifest"
            if os.path.exists(mfn):
                print("  skip: eixsting manifest")
                continue
            """
            chipid/single high resolution photos
            """
            single_dir = os.path.join(chipid_dir, "single")
            if os.path.exists(single_dir):
                for base_fn in sorted(os.listdir(single_dir)):
                    print(f"  check {base_fn}")
                    if ".thumb" in base_fn:
                        print("    Skip .thumb")
                        continue
                    fn_orig = os.path.join(single_dir, base_fn)
                    if not ".jpg" in fn_orig and not ".tif" in fn_orig and not ".png" in fn_orig:
                        raise ValueError("Unexpected fn %s" % fn_orig)
                    base_fn_new = single_fn_add_user(base_fn,
                                                     collection=new_collection)
                    print(f"    {base_fn} => {base_fn_new}")
                    fn_new = os.path.join(single_dir, base_fn_new)
                    reg_fn = os.path.join("single", base_fn_new)
                    print(f"    manfesting image: {reg_fn}")
                    print(f"    mv {fn_orig} => {fn_new}")
                    if not dry:
                        shutil.move(fn_orig, fn_new)
                        simap.map_manifest_add_file(chipid_dir,
                                                    reg_fn,
                                                    collection=new_collection,
                                                    type_="image")
            """
            Map file
            """
            for index_fn in sorted(glob.glob(chipid_dir + "/*/index.html")):
                print(f"  check {index_fn}")
                orig_map_dir = os.path.basename(os.path.dirname(index_fn))
                new_map_dir = new_collection + "_" + orig_map_dir
                fn_orig = os.path.join(chipid_dir, orig_map_dir)
                fn_new = os.path.join(chipid_dir, new_map_dir)
                print(f"    manfesting map: {new_map_dir}")
                print(f"    mv {fn_orig} => {fn_new}")
                if not dry:
                    shutil.move(fn_orig, fn_new)
                    simap.map_manifest_add_file(chipid_dir,
                                                new_map_dir,
                                                collection=new_collection,
                                                type_="map")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rewrite a page to point to new URL scheme")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("--ignore-errors", action="store_true")
    parser.add_argument("--fndir")
    args = parser.parse_args()
    run(args.fndir, dry=args.dry, ignore_errors=args.ignore_errors)


if __name__ == "__main__":
    main()
