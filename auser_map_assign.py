#!/usr/bin/env python3
"""
Use copyright databases to rename files in /map
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
import json
from sipr0n import env
import datetime


def match_db_entry(db, vendor, chipid, basename, type_):
    """
    "ad633jnz-fake": [
        {
            "basename": "mz_mit20x",
            "chipid": "ad633jnz-fake",
            "collection": "mcmaster",
            "file_year": 2022,
            "map_copyright": "&copy; 2020 John McMaster, CC-BY",
            "map_copyright_year": 2020,
            "type": "map",
            "vendor": "ad"
        }
    ],


        {
            "basename": "mz_mit20x2",
            "chipid": "adm213-ears",
            "collection": "mcmaster",
            "type": "map",
            "vendor": "ad"
        },
        {
            "basename": "mz_mit20x2.jpg",
            "chipid": "adm213-ears",
            "collection": "mcmaster",
            "dirname": "single",
            "type": "image",
            "vendor": "ad"
        }
    """
    vendorj = db.get(vendor, {})
    ret = []
    for entryj in vendorj.get(chipid, []):
        if entryj.get("type") != type_:
            continue
        if basename == entryj.get("basename"):
            ret.append(entryj)
    if len(ret) == 0:
        return None
    elif len(ret) == 1:
        return ret[0]
    else:
        print(ret)
        raise Exception("too many matches")


def collection_assign_map(url, archive_db=None, map_db=None):
    vendor, chipid, _old_collection, flavor = util.parse_map_url_vcuf(url)
    archive_entry = match_db_entry(archive_db,
                                   vendor,
                                   chipid,
                                   flavor,
                                   type_="map")
    map_entry = match_db_entry(map_db, vendor, chipid, flavor, type_="map")
    if archive_entry is None and map_entry is None:
        return None
    elif archive_entry is not None and map_entry is not None:
        archive_c = archive_entry.get("collection")
        map_c = map_entry.get("collection")
        # Want to see how many mismatch
        # But in general suggest keeping archive as canonical if need automatic resolution
        if map_c and map_c != archive_c:
            print("  WARNING: collection mismatch")
            print(f"    /map:     {map_c}")
            print(f"    /archive: {archive_c}")
        ret = map_entry
    elif archive_entry is not None:
        # All archive entries should be attributed
        ret = archive_entry
    else:
        # Some maps are missing copyright strings
        ret = map_entry

    # Estimate year
    # Use copyright string if given, otherwise file timestamp
    if ret.get("map_copyright_year"):
        ret["copyright_year"] = ret["map_copyright_year"]
    # hmm obscure failure on here w/
    elif "file_year" in ret:
        ret["copyright_year"] = ret["file_year"]
    return ret


def collection_assign_single(basename, archive_db=None, map_db=None):
    ret_entry = None
    vendor, chipid, old_collection, flavor, ext = util.parse_map_image_vcufe(
        basename)
    basename2 = flavor + "." + ext
    archive_entry = match_db_entry(archive_db,
                                   vendor,
                                   chipid,
                                   basename2,
                                   type_="image")
    map_entry = match_db_entry(map_db,
                               vendor,
                               chipid,
                               basename2,
                               type_="image")
    if archive_entry is None and map_entry is None:
        print(f"  No archive or map matches on {basename} => {basename2}")
        return None
    elif archive_entry is not None and map_entry is not None:
        archive_c = archive_entry.get("collection")
        map_c = map_entry.get("collection")
        # Want to see how many mismatch
        # But in general suggest keeping archive as canonical if need automatic resolution
        if map_c and map_c != archive_c:
            print(map_c, archive_c)
            raise Exception("mismatch")
        ret_entry = map_entry
    elif archive_entry is not None:
        # Hmm maybe better to take copyright year from .html
        # handle in post?
        ret_entry = archive_entry
    else:
        ret_entry = map_entry

    # map copyright strings are more reliable
    # Fallback: see if we can guess it based on a corresponding map file
    map_url = "map/" + vendor + "/" + chipid + "/" + old_collection + "_" + flavor + "/index.html"
    map_map_entry = collection_assign_map(map_url,
                                          archive_db=archive_db,
                                          map_db=map_db)
    if map_map_entry:
        map_copyright_year = map_map_entry.get("map_copyright_year")
        if map_copyright_year:
            ret_entry["copyright_year"] = map_copyright_year
            print(f"  Single: inherit map year {map_copyright_year}")
    else:
        print(f"  Single: Failed to locate year via {map_url}")

    return ret_entry


def single_fn_rename_collection(fn, collection):
    vendor, chipid, _old_collection, flavor, ext = util.parse_map_image_vcufe(
        fn)
    return util.map_image_uvcfe_to_basename(vendor, chipid, collection, flavor,
                                            ext)


def map_fn_rename_collection(fn, collection):
    _old_collection, flavor = util.parse_map_basename_uf(fn)
    return collection + "_" + flavor


def run(archive_db=None, map_db=None, dry=False, ignore_errors=False):
    archive_db = json.load(open(archive_db))
    map_db = json.load(open(map_db))
    env.setup_env_default()

    mapdir = env.MAP_DIR
    new_collection = "unknown"
    assert "www/map" in mapdir
    assert os.path.basename(mapdir) == "map"
    for vendor_dir in sorted(os.listdir(mapdir)):
        vendor_dir = os.path.join(mapdir, vendor_dir)
        if not os.path.isdir(vendor_dir):
            print("skip non-dir", vendor_dir)
            continue
        for chipid_dir in sorted(os.listdir(vendor_dir)):
            print("")
            chipid_dir = os.path.join(vendor_dir, chipid_dir)
            print("Check", chipid_dir)

            single_dir = os.path.join(chipid_dir, "single")
            if os.path.exists(single_dir):
                for base_fn in sorted(os.listdir(single_dir)):
                    print(f"Found single/{base_fn}")
                    fn_orig = os.path.join(single_dir, base_fn)
                    if not os.path.isfile(fn_orig):
                        print("  skip non-file")
                        continue
                    if ".thumb" in base_fn:
                        # Instead of fixing thumbnails, just regenerate them
                        print(f"  rm {fn_orig}")
                        if not dry:
                            os.unlink(fn_orig)
                    else:
                        if not ".jpg" in fn_orig and not ".tif" in fn_orig and not ".png" in fn_orig and not ".xcf" in fn_orig:
                            raise ValueError("Unexpected fn %s" % fn_orig)
                        new_meta = collection_assign_single(
                            base_fn, archive_db=archive_db, map_db=map_db)
                        if not new_meta:
                            print("  Completely failed to assign :(")
                        else:
                            if "copyright_year" not in new_meta:
                                file_year = datetime.datetime.fromtimestamp(
                                    os.path.getctime(fn_orig)).year
                                new_meta["copyright_year"] = file_year
                                print(f"  Detect file year {file_year}")
                            new_collection = new_meta.get("collection")
                            if not new_collection:
                                print("  Matched w/o collection :(")
                                manifest_fn = fn_orig
                            else:
                                print(f"  Matched collection {new_collection}")
                                base_fn_new = single_fn_rename_collection(
                                    base_fn, collection=new_collection)
                                print(f"  {base_fn} => {base_fn_new}")
                                fn_new = os.path.join(single_dir, base_fn_new)
                                reg_fn = os.path.join("single", base_fn_new)
                                manifest_fn = reg_fn
                                print(f"  mv {fn_orig} => {fn_new}")
                                if not dry:
                                    shutil.move(fn_orig, fn_new)

                            copyright_year = new_meta["copyright_year"]
                            print(
                                f"  manifesting image: {manifest_fn}, year={copyright_year}"
                            )
                            if not dry:
                                simap.map_manifest_add_file(
                                    chipid_dir,
                                    manifest_fn,
                                    collection=new_meta.get("collection"),
                                    copyright_year=copyright_year,
                                    type_="image")
            """
            Map file
            """
            for index_fn in sorted(glob.glob(chipid_dir + "/*/index.html")):
                print(f"Found {index_fn}")
                orig_map_dir = os.path.basename(os.path.dirname(index_fn))
                new_meta = collection_assign_map(index_fn,
                                                 archive_db=archive_db,
                                                 map_db=map_db)
                if not new_meta:
                    print("  Completely failed to assign :(")
                else:
                    new_collection = new_meta.get("collection")
                    if not new_collection:
                        print("  Matched w/o collection :(")
                        manifest_fn = orig_map_dir
                    else:
                        print(f"  Matched collection {new_collection}")
                        base_fn_new = map_fn_rename_collection(
                            orig_map_dir, collection=new_collection)
                        fn_orig = os.path.join(chipid_dir, orig_map_dir)
                        fn_new = os.path.join(chipid_dir, base_fn_new)
                        manifest_fn = base_fn_new
                        print(f"  mv {fn_orig} => {fn_new}")
                        if not dry:
                            shutil.move(fn_orig, fn_new)
                    copyright_year = new_meta["copyright_year"]
                    print(
                        f"  manifesting map: {manifest_fn}, year={copyright_year}"
                    )
                    if not dry:
                        simap.map_manifest_add_file(
                            chipid_dir,
                            manifest_fn,
                            collection=new_meta.get("collection"),
                            copyright_year=copyright_year,
                            type_="map")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Assign copyright to files in /map")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("--archive-db")
    parser.add_argument("--map-db")
    args = parser.parse_args()
    run(archive_db=args.archive_db, map_db=args.map_db, dry=args.dry)


if __name__ == "__main__":
    main()
