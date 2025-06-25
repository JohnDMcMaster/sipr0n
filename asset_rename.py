#!/usr/bin/env python3

import shutil
import re
import os
import glob
from pathlib import Path
import traceback
from sipr0n import util
from sipr0n import env
import subprocess

def parse_vendor_chipid(vendor_chipid):
    vendor, chipid = vendor_chipid.split("_")
    util.validate_vendor(vendor)
    util.validate_chipid(chipid)
    return vendor, chipid

def diff_strings(s1, s2):
    fn1 = "/tmp/si_left.txt"
    fn2 = "/tmp/si_right.txt"
    with open(fn1, "w") as f:
        f.write(s1)
    with open(fn2, "w") as f:
        f.write(s2)

    print("")
    print("****************************************")
    print("diff")
    subprocess.run(["diff", "-w", fn1, fn2], check=False, stderr=subprocess.PIPE)
    print("****************************************")
    print("")

def rename_page(old_vcu, new_vcu, dry):
    """
    Assume there aren't many pages effected
    """
    old_vendor, old_chipid, old_user = old_vcu
    new_vendor, new_chipid, new_user = new_vcu
    assert old_user == new_user
    user = old_user

    move_files = []
    old_page_fn = os.path.join(env.WWW_DIR + f"/archive/data/pages/{user}/{old_vendor}/{old_chipid}.txt")
    new_page_fn = os.path.join(env.WWW_DIR + f"/archive/data/pages/{user}/{new_vendor}/{new_chipid}.txt")
    if not os.path.exists(old_page_fn):
        print("  WARNING: old page does not exist")
    else:
        """
        Look at the image
        """
        print(f"  Page: found {user}:{old_vendor}:{old_chipid}")
        with open(old_page_fn, "r") as f:
            page_txt = f.read()
        # Image reference
        # {{:mcmaster:efabless:gf-mpw18h1-slot4-openfasoc:pack_top.jpg?300|}}
        page_txt = page_txt.replace("{old_vendor}:{old_chipid}", "{new_vendor}:{new_chipid}")
        page_txt_new = page_txt
        # Page reference
        # [[https://siliconpr0n.org/map/efabless/gf-mpw18h1-slot4-openfasoc/mcmaster_mit20x/|mit20x]]
        # * [[https://siliconpr0n.org/map/efabless/gf-mpw18h1-slot4-openfasoc/single/efabless_gf-mpw18h1-slot4-openfasoc_mcmaster_mit20x.jpg|Single]] (22444x17485, 41.3425MiB)
        page_txt_new = page_txt_new.replace(f"/{old_vendor}/{old_chipid}/", f"/{new_vendor}/{new_chipid}/")
        page_txt_new = page_txt_new.replace(f"/{old_vendor}_{old_chipid}_", f"/{new_vendor}_{new_chipid}_")
        # vendor_efabless => vendor_tiny-tapeout
        page_txt_new = page_txt_new.replace(f"vendor_{old_vendor}", f"vendor_{new_vendor}")
        if page_txt_new == page_txt:
            print(page_txt_new)
        else:
            diff_strings(page_txt, page_txt_new)
        print("  Write new txt")
        if not dry:
            with open(old_page_fn, "w") as f:
                f.write(page_txt_new)
        # FIXME: sudo -u www-data mkdir /var/www/archive/data/pages/infosecdj/tiny-tapeout/
        print(f"  mv {old_page_fn} {new_page_fn}")
        if not dry:
            shutil.move(old_page_fn, new_page_fn)


    old_data_dir = os.path.join(env.WWW_DIR + f"/archive/data/media/{user}/{old_vendor}/{old_chipid}")
    new_data_dir = os.path.join(env.WWW_DIR + f"/archive/data/media/{user}/{new_vendor}/{new_chipid}")
    if not os.path.exists(old_data_dir):
        print("  WARNING: old data dir does not exist")
    else:
        print(f"  mv {old_data_dir} {new_data_dir}")
        if not dry:
            shutil.move(old_data_dir, new_data_dir)


def run(old_vendor_chipid, new_vendor_chipid, dry=True):
    env.setup_env_default()

    assert old_vendor_chipid != new_vendor_chipid, old_vendor_chipid
    old_vendor, old_chipid = parse_vendor_chipid(old_vendor_chipid)
    new_vendor, new_chipid = parse_vendor_chipid(new_vendor_chipid)
    print(f"{old_vendor} {old_chipid} => {new_vendor} {new_chipid}")
    assert (old_vendor, old_chipid) != (new_vendor, new_chipid)

    glob_str = env.WWW_DIR + f"/archive/data/pages/*/{old_vendor}/{old_chipid}.txt"
    print("Checking " + glob_str)
    old_page_fns = glob.glob(glob_str)
    print("Found %u pages" % len(old_page_fns))
    for old_page_fn in old_page_fns:
        old_user = old_page_fn.split("/")[-3]
        print(f"  page user {old_user}")
        rename_page((old_vendor, old_chipid, old_user), (new_vendor, new_chipid, old_user), dry=dry)

    def move_map_files():
        old_map_root_dir = env.WWW_DIR + f"/map/{old_vendor}/{old_chipid}"
        new_map_root_dir = env.WWW_DIR + f"/map/{new_vendor}/{new_chipid}"
        if not os.path.exists(old_map_root_dir):
            print("Map dir: not present")
        else:
            print("Map dir: found")
            if os.path.exists(new_map_root_dir):
                assert "FIXME: multi dir merge not supported"
                '''
                print("New map dir already exists. Moving individual assets")
                for src_file in glob.glob(env.WWW_DIR + f"/map/{old_vendor}/{old_chipid}/single/*"):
                    dst_file = os.path.join(new_map_root_dir, "single", os.path.basename(src_file))
                    print("mv {src_file} {dst_file}")
                    if not dry:
                        shutil.move(src_file, dst_file)
                old_files = glob.glob(env.WWW_DIR + f"/map/{old_vendor}/{old_chipid}/*")
                old_map_html_dirs = glob.glob(env.WWW_DIR + f"/map/{old_vendor}/{old_chipid}/*")
                '''
            else:
                print(f"  mv {old_map_root_dir} {new_map_root_dir}")
                if not dry:
                    shutil.move(old_map_root_dir, new_map_root_dir)

    def rename_single_images():
        # Moved into new dir but not necessarily renamed
        old_map_single_images = list(glob.glob(env.WWW_DIR + f"/map/{new_vendor}/{new_chipid}/single/{old_vendor}_{old_chipid}_*")) + list(glob.glob(env.WWW_DIR + f"/map/{old_vendor}/{old_chipid}/single/{old_vendor}_{old_chipid}_*"))
        print("Map single images: %u" % len(old_map_single_images))
        for old_fn in old_map_single_images:
            new_fn = old_fn.replace(f"{old_vendor}_{old_chipid}", f"{new_vendor}_{new_chipid}")
            if old_fn == new_fn:
                print(f"  Already renamed: {old_fn}")
            else:
                print(f"  mv {old_fn} {new_fn}")
                if not dry:
                    shutil.move(old_fn, new_fn)

    rename_single_images()
    move_map_files()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename a vendor + chipid, updating map files + wiki pages (best effort)")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("old_vendor_chipid")
    parser.add_argument("new_vendor_chipid")
    args = parser.parse_args()
    run(old_vendor_chipid=args.old_vendor_chipid, new_vendor_chipid=args.new_vendor_chipid, dry=args.dry)


if __name__ == "__main__":
    main()
