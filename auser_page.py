#!/usr/bin/env python3

import shutil
import re
import os
import glob
from pathlib import Path
import traceback


def parse_fn_uvc(fn):
    """
    Canonical name like
    vendor_chipid_user_flavor.ext
    """
    # Normalize if a canonical path was given
    m = re.search(r'data/pages/([a-z0-9\-]+)/([a-z0-9\-]+)/([a-z0-9\-]+).txt',
                  fn)
    if m:
        user = m.group(1)
        vendor = m.group(2)
        chipid = m.group(3)
    else:
        # Otherwise just use the username
        m = re.search(r'data/pages/([a-z0-9\-]+)/', fn)
        if not m:
            raise Exception("Non-confirming file name: %s" % (fn, ))
        user = m.group(1)
        vendor = None
        chipid = None
    return (user, vendor, chipid)


def parse_map_url_vc(url):
    m = re.search(r'siliconpr0n.org/map/([a-z0-9\-]+)/([a-z0-9\-]+)/', url)
    if not m:
        raise Exception("Non-confirming file name: %s" % (url, ))
    vendor = m.group(1)
    chipid = m.group(2)
    return (vendor, chipid)


def parse_single_url_vc(url):
    m = re.search(
        r'siliconpr0n.org/map/([a-z0-9\-]+)/([a-z0-9\-]+)/single/([a-z0-9\-]+)_([a-z0-9\-]+)',
        url)
    if not m:
        raise Exception("Non-confirming file name: %s" % (url, ))
    _vendor = m.group(1)
    _chipid = m.group(2)
    vendor = m.group(3)
    chipid = m.group(4)
    return (vendor, chipid)


def run_page(fn, dry=False):
    # Already ran?
    if os.path.exists(fn + ".nouser"):
        print("SKIP:", fn)
        return
    """
    data/pages/user/vendor/chipid.txt
    """
    user, page_vendor, page_chipid = parse_fn_uvc(fn)
    print(f"  Page info")
    print(f"    user: {user}")
    print(f"    vendor: {page_vendor}")
    print(f"    chipid: {page_chipid}")
    txt_orig = open(fn, "r").read()
    txt = open(fn, "r").read()
    """
    Old url:
    https://siliconpr0n.org/map/intel/80c186/mz_mit20x/
    https://siliconpr0n.org/map/intel/80c186/single/intel_80c186_mz_mit20x.jpg

    new:
    https://siliconpr0n.org/map/intel/80c186/mcmaster_mz_mit20x/
        but not single...
        maybe patch in next step
    https://siliconpr0n.org/map/intel/80c186/single/intel_80c186_mcmaster_mz_mit20x.jpg

    Both can be handled by simple find and replace
    siliconpr0n.org/map/intel/80c186/ => siliconpr0n.org/map/intel/80c186/mcmaster_
    siliconpr0n.org/map/intel/80c186/single/intel_80c186_ => siliconpr0n.org/map/intel/80c186/single/intel_80c186_mcmaster_
    """
    has_url = False
    for url in re.findall(r'(https?://[^\s]+)', txt):
        has_url = True
        # [[https://siliconpr0n.org/map/intel/80502/mz_mit5x/|MZ @ mit5x]]
        # https://siliconpr0n.org/map/intel/80502/mz_mit5x/|MZ
        print("  url", url)
        ppos = url.find("|")
        if ppos >= 0:
            url = url[0:ppos]

        if "siliconpr0n.org/map" not in url:
            print("    Skip")
            continue
        map_vendor, map_chipid = parse_map_url_vc(url)
        if page_vendor and page_chipid:
            if (page_vendor, page_chipid) != (map_vendor, map_chipid):
                print("Page based:", page_vendor, page_chipid)
                print("/map based:", map_vendor, map_chipid)
                raise Exception("Unexpected URL")
        vendor = map_vendor
        chipid = map_chipid

        if "/single/" in url:
            single_vendor, single_chipid = parse_single_url_vc(url)
            if (vendor, chipid) != (single_vendor, single_chipid):
                print("Page based:   ", vendor, chipid)
                print("/single based:", single_vendor, single_chipid)
                raise Exception("Unexpected URL")

            r1 = f"single/{vendor}_{chipid}"
            r2 = f"single/{vendor}_{chipid}_{user}"
            new = url.replace(r1, r2)
        else:
            # should end in /
            assert re.match("https?://siliconpr0n.org/map/.+/", url)
            new = url.replace(f"{vendor}/{chipid}/",
                              f"{vendor}/{chipid}/{user}_")
        old1 = str(txt)
        print("    Old", url)
        print("    New", new)
        txt = txt.replace(url, new)
        assert old1 != txt

    if not has_url:
        print("  SKIP: no URLs")
    elif txt_orig == txt:
        print("  WARNING: unmodified")
    else:
        if dry:
            if 0:
                print("")
                print("")
                print("")
                print(txt)
        else:
            shutil.move(fn, fn + ".nouser")


def run(fndir, dry=False, ignore_errors=False):
    if ".txt" in fndir:
        assert os.path.isfile(fndir)
        run_page(fndir, dry=dry)
    else:
        assert "data/pages" in fndir
        assert os.path.basename(fndir) == "pages"
        errors = 0
        nusers = 0
        npages = 0
        for user_dir in glob.glob("%s/*" % fndir):
            start_page = os.path.join(user_dir, "start.txt")
            if not os.path.exists(start_page):
                continue
            start_txt = open(start_page, "r").read()
            # Must be a user page
            if "{{tag>collection}}" not in start_txt:
                continue
            nusers += 1
            # Now recurse and find all vendor/chipid pages
            for path in Path(user_dir).rglob('*.txt'):
                path = str(path)
                print("Page:", path)
                try:
                    npages += 1
                    run_page(path, dry=dry)
                except:
                    errors += 1
                    if ignore_errors:
                        traceback.print_exc()
                    else:
                        raise
            print("Users: %u" % nusers)
            print("Pages: %u" % npages)
            print("Errors: %u" % errors)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rewrite a page to point to new URL scheme")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--ignore-errors", action="store_true")
    parser.add_argument("fndir")
    args = parser.parse_args()
    run(args.fndir, dry=args.dry, ignore_errors=args.ignore_errors)


if __name__ == "__main__":
    main()
