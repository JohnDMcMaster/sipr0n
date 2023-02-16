#!/usr/bin/env python3
import auser_page
import os
import traceback
from sipr0n import util
import glob
from pathlib import Path
import re
import json
import datetime
from sipr0n import metadata
from sipr0n import env


def html2meta(txt):
    # auto generated
    # Make some assumptions how its formatted
    # initViewer({"tilesAlignedTopLeft": true, "scale": null, ... , "name_raw": "???"});
    for l in txt.split("\n"):
        if l.find("initViewer") < 0:
            continue
        js = l.strip().replace("initViewer(", "").replace(");", "")
        return json.loads(js)
    raise ValueError("unexpected page")


def guess_collection(person_cc, copyright_db):
    """
    | drdecap       | Dr. Decap                                                      |       |
    | furrtek       | Furrtek CC BY 4.0                                              |       |
    | goodspeed     | Travis Goodspeed, CC0                                          |       |
    | marchcat      | FIXME                                                          |       |
    | marmontel     | Boris Marmontel, CC BY 4.0                                     |       |
    | nico          | nico <xxx@xxx.net>, CC BY 3.0     
    """
    person_cc = person_cc.split(",")[0].split("CC")[0]
    print("Guessing:", person_cc)
    if person_cc == "FIXME" or not person_cc:
        return None
    for this_collection, cstr in copyright_db.items():
        cstr = cstr.split(",")[0].split("CC")[0]
        if person_cc == cstr:
            return this_collection


def run_page(fn, meta, copyright_db):
    pagej = html2meta(open(fn).read())
    # Stack overflow argues this isn't proper but seems to work well enough
    file_year = datetime.datetime.fromtimestamp(os.path.getctime(fn)).year
    # "copyright": "&copy; 2022 Travis Goodspeed, CC0"}]
    # "copyright": ""
    map_copyright = pagej["layers"][0].get("copyright", "")

    parsed_year = None
    parsed_collection = None
    if map_copyright:
        # 2014 John McMaster, CC BY-NC-SA
        # oof so old doens't have copyright string
        # add extra copyright on front as hack
        # The second / extra will be ignored if present
        if "&copy;" not in map_copyright:
            map_copyright = "&copy; " + map_copyright

        m = re.match(r"&copy; ([0-9]+) (.+)", map_copyright)
        if m:
            parsed_year = int(m.group(1))
            person_cc = m.group(2)
            parsed_collection = guess_collection(person_cc, copyright_db)
        else:
            # &copy;  Travis Goodspeed, CC0
            # uggghhh
            m = re.match(r"&copy; (.+)", map_copyright)
            if m:
                person_cc = m.group(1)
                parsed_collection = guess_collection(person_cc, copyright_db)
            else:
                print(map_copyright)
                assert 0
        print("collection", parsed_collection, "from", map_copyright)

    # www/map/wch/wch340g/mz_10x/index.html => mz_10x
    map_dir = os.path.basename(os.path.dirname(fn))
    map_vendor, map_chipid = util.parse_map_local_vc(fn)
    metaj = metadata.add_meta_map(meta,
                                  vendor=map_vendor,
                                  chipid=map_chipid,
                                  collection=parsed_collection,
                                  basename=map_dir)
    metaj["file_year"] = file_year
    if map_copyright:
        metaj["map_copyright"] = map_copyright
    if parsed_year:
        metaj["map_copyright_year"] = parsed_year
    if parsed_collection:
        metaj["collection"] = parsed_collection


def run(fndir=None, fn_out=None, ignore_errors=False):
    """
    Search /wiki and try to guess linked images based on collection
    """
    meta = {}
    copyright_db = metadata.load_copyright_db()
    env.setup_env_default()
    if fndir:
        assert ".html" in fndir
        assert os.path.isfile(fndir)
        run_page(fndir, meta, copyright_db=copyright_db)
    else:
        fndir = env.MAP_DIR
        assert "www/map" in fndir
        assert os.path.basename(fndir) == "map"

        def topage(fn):
            pos = fndir.find("www/map")
            fn = fn[pos + len("www/map"):]
            return "https://siliconpr0n.org/map/" + fn

        errors = 0
        npages = 0
        for vendor_dir in glob.glob("%s/*" % fndir):
            # print(vendor_dir)
            for chipid_dir in glob.glob("%s/*" % vendor_dir):
                # print(chipid_dir)
                for html_page in glob.glob("%s/*/index.html" % chipid_dir):
                    print("Page:", html_page)
                    print("  %s" % topage(html_page))
                    try:
                        npages += 1
                        run_page(html_page, meta, copyright_db=copyright_db)
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
        print("Pages: %u" % npages)
        print("Errors: %u" % errors)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rewrite a page to point to new URL scheme")
    parser.add_argument("--ignore-errors", action="store_true")
    parser.add_argument("--fndir")
    parser.add_argument("fn_out", nargs="?")
    args = parser.parse_args()
    run(args.fndir, fn_out=args.fn_out, ignore_errors=args.ignore_errors)


if __name__ == "__main__":
    main()
