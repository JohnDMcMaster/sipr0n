#!/usr/bin/env python3
import auser_page
import os
import traceback
from sipr0n import util
import glob
from pathlib import Path
import re
import json
"""
Think this format should be shuffle agnostic
NOTE: there may be collisions for a (vendor, chipid, basename)
We'll have to see how easy they are to resolve / how many

{
    "altera": {
        "ep900": [
            {
                "type": "map",
                "collection": "mcmaster",
                "vendor": "altera",
                "chipid": "ep900",
                "basename": "mz_mit20x",
            }
            {
                "type": "image",
                "collection": "mcmaster",
                "vendor": "altera",
                "chipid": "ep900",
                "dirname": "single",
                "basename": "mz_mit20x.jpg",
            }
        ],
    }
}
"""


class VCMismatch(Exception):
    pass


def add_meta_image(meta, vendor, chipid, collection, dirname, basename):
    assert vendor
    assert chipid
    assert collection
    assert basename
    assert dirname
    j = {
        "type": "image",
        "collection": collection,
        "vendor": vendor,
        "chipid": chipid,
        "dirname": dirname,
        "basename": basename,
    }

    vendorj = meta.setdefault(vendor, {})
    chipidj = vendorj.setdefault(chipid, [])
    chipidj.append(j)
    print(f"    image from {collection}: {vendor} {chipid} {basename}")


def add_meta_map(meta, vendor, chipid, collection, basename):
    assert vendor
    assert chipid
    assert collection
    assert basename
    j = {
        "type": "map",
        "collection": collection,
        "vendor": vendor,
        "chipid": chipid,
        "basename": basename,
    }

    vendorj = meta.setdefault(vendor, {})
    chipidj = vendorj.setdefault(chipid, [])
    chipidj.append(j)
    print(f"    map from {collection}: {vendor} {chipid} {basename}")


def run_page(fn, meta, dry=False):
    """
    Assume that links on page are correctly attributed
    This is important as they are already canonical
    (ie via auser_page.py)

    data/pages/user/vendor/chipid.txt
    """
    # Has the wiki been annotated to have links yet
    archive_collection_links = False

    collection, page_vendor, page_chipid = auser_page.parse_page_fn_uvc(fn)

    has_url = False
    txt = open(fn, "r").read()
    ignore_errors = False
    if "{{tag>auser_ignore_errors}}" in txt:
        ignore_errors = True
    for url in re.findall(r'(https?://[^\s]+)', txt):
        has_url = True
        # [[https://siliconpr0n.org/map/intel/80502/mz_mit5x/|MZ @ mit5x]]
        # https://siliconpr0n.org/map/intel/80502/mz_mit5x/|MZ
        print("  url", url)
        ppos = url.find("|")
        if ppos >= 0:
            url = url[0:ppos]

        if "siliconpr0n.org/map" not in url:
            print("    Skip: not a /map URL")
            continue
        url_vendor, url_chipid = util.parse_map_url_vc(url)
        # These will probably happen but are more likely to be errors
        # Need a whitelist?
        if page_vendor is not None:
            if page_vendor != url_vendor or page_chipid != url_chipid:
                print(
                    "    WARNING: page vendor/chipid does not match URL vendor/chipid"
                )
                print("      Page: ", page_vendor, page_chipid)
                print("      URL:  ", url_vendor, url_chipid)
                if not ignore_errors:
                    raise VCMismatch(
                        "page vendor/chipid does not match URL vendor/chipid")

        if "/single/" in url:
            single_fn = os.path.basename(url)
            if archive_collection_links:
                single_vendor, single_chipid, _collection, flavor, ext = util.parse_map_image_vcufe(
                    single_fn)
            else:
                single_vendor, single_chipid, flavor, ext = util.parse_map_image_vcfe(
                    single_fn)
            basename = flavor + "." + ext
            add_meta_image(meta,
                           vendor=single_vendor,
                           chipid=single_chipid,
                           collection=collection,
                           dirname="single",
                           basename=basename)
        else:
            # should end in /
            assert re.match("https?://siliconpr0n.org/map/.+/", url)
            map_dir = os.path.basename(os.path.dirname(url))
            map_vendor, map_chipid = util.parse_map_url_vc(url)
            add_meta_map(meta,
                         vendor=map_vendor,
                         chipid=map_chipid,
                         collection=collection,
                         basename=map_dir)

    if not has_url:
        print("  SKIP: no URLs")


def run(fndir, fn_out=None, dry=False, ignore_errors=False):
    """
    Search /wiki and try to guess linked images based on collection
    """
    meta = {}
    if ".txt" in fndir:
        assert os.path.isfile(fndir)
        run_page(fndir, meta, dry=dry)
    else:
        assert "data/pages" in fndir
        assert os.path.basename(fndir) == "pages"

        def topage(fn):
            pos = fndir.find("data/pages")
            fn = fn[pos + len("data/pages"):]
            fn = fn.replace(".txt", "")
            return "https://siliconpr0n.org/archive/doku.php?id=" + fn.replace(
                "/", ":")

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
                print("  %s" % topage(path))
                try:
                    npages += 1
                    run_page(path, meta, dry=dry)
                except Exception as e:
                    errors += 1
                    if ignore_errors:
                        traceback.print_exc()
                    else:
                        raise
        js = json.dumps(meta, sort_keys=True, indent=4, separators=(',', ': '))
        if fn_out:
            open(fn_out, "w").write(js)
        else:
            print("")
            print("")
            print("")
            print(js)
            print("")
            print("")
            print("")
        print("Users: %u" % nusers)
        print("Pages: %u" % npages)
        print("Errors: %u" % errors)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rewrite a page to point to new URL scheme")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("--ignore-errors", action="store_true")
    parser.add_argument("fndir")
    parser.add_argument("fn_out", nargs="?")
    args = parser.parse_args()
    run(args.fndir,
        fn_out=args.fn_out,
        dry=args.dry,
        ignore_errors=args.ignore_errors)


if __name__ == "__main__":
    main()
