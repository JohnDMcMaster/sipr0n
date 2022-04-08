#!/usr/bin/env python3
"""
Clean up using
find -name 'index.html.*' -delete


https://github.com/JohnDMcMaster/sipr0n/issues/11

let's find / fix the broken pages
to do this:
-correlate map's to images
-use pr0nmap to generate just .html
-parse both .html files
-emit a warning if they differ
-if replace:
    wriew .new
    move previous to .orig
"""

import subprocess
import re
import os
import glob
import json
import pr0nmap
from pr0nmap.groupxiv import GroupXIV
from pr0nmap.groupxiv import write_js_meta
from pr0nmap.map import ImageMapSource
import shutil
import copy
import img2doku


def extract_html_meta(fn):
    """
    initViewer({"tilesAlignedTopLeft": true, "scale": null, "layers": [{"imageSize": 4096, "tileExt": ".jpg", "width": 31000, "height": 31000, "URL": "l1", "tileSize": 250, "name": "???", "copyright": "2018 John McMaster, CC BY"}], "name": "out, &copy;2018 John McMaster, CC BY", "name_raw": "out"});
    """
    for l in open(fn, "r"):
        if "initViewer" in l:
            break
    else:
        raise Exception("Failed to find initViewer")
    l = l.strip()
    l = l.replace("initViewer(", "")
    # remove );
    l = l[:-2]
    j = json.loads(l)
    return j


def img2j(img_fn):
    tmp_dir = "img2j_tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    try:
        # Scraped from pr0nmap.main
        source = ImageMapSource(img_fn, threads=1)
        m = GroupXIV(source, copyright="copyright")
        m.set_title("title")
        m.set_js_only(True)
        m.set_skip_missing(True)
        m.set_out_dir(tmp_dir)
        m.set_im_ext(None)

        m.run()

        j = extract_html_meta(tmp_dir + "/index.html")
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

    return j


def shift_existing_fn(fn):
    if not os.path.exists(fn):
        return
    i = 0
    while True:
        new_fn = "%s.%u" % (fn, i)
        if not os.path.exists(new_fn):
            print("mv %s => %s" % (fn, new_fn))
            shutil.move(fn, new_fn)
            return
        i += 1


def run(map_dir, dry=False, verbose=False):
    """
    It's better to look at images to dirs
    Doesn't always go the other way
    """
    for img_fn in glob.glob(map_dir + "/single/*.jpg"):
        if ".thumb.jpg" in img_fn:
            continue
        print("Checking %s" % img_fn)
        _fnbase, _vendor, _chipid, flavor = img2doku.parse_image_name(img_fn)
        html_fn = map_dir + "/" + flavor + "/index.html"
        if not os.path.isfile(html_fn):
            print("WARNING: could not find HTML: %s" % html_fn)
            continue
        run_pair(img_fn=img_fn, html_fn=html_fn, dry=dry, verbose=verbose)


def run_pair(img_fn, html_fn, dry=False, verbose=False):
    print("Extracting old HTML")
    j_html = extract_html_meta(html_fn)
    print("Generating new HTML")
    j_img = img2j(img_fn)

    print("")

    print("HTML")
    print(j_html)

    print("")

    print(".JPG")
    print(j_img)

    print("")
    """
    "imageSize": 4096, "tileExt": ".jpg", "width": 31000, "height": 31000,


    HTML
      Top name: 'out, &copy;2018 John McMaster, CC BY'
      Layer name: '???'
      Layer copyright: '2018 John McMaster, CC BY'
    imageSize
      HTML: 4096
      .JPG: 32000
    width
      HTML: 31000
      .JPG: 30811
    height
      HTML: 31000
      .JPG: 30989
    """
    if len(j_html["layers"]) != 1:
        print("WARNING: non-standard layer stackup. Skipping")
        return

    l1h = j_html["layers"][0]
    l1i = j_img["layers"][0]
    print("HTML")
    # Becomes title bar on window
    print("  Top name: '%s'" % j_html["name"])
    print("  Top copyright: '%s'" % j_html.get("copyright", ""))
    # Shown in lower right before layer copyright
    print("  Layer name: '%s'" % l1h["name"])
    # Shown in lower right. Copyright (C) is added by GroupXIV
    print("  Layer copyright: '%s'" % l1h.get("copyright", ""))
    print("imageSize")
    print("  HTML: %u" % l1h["imageSize"])
    print("  .JPG: %u" % l1i["imageSize"])
    print("width")
    print("  HTML: %u" % l1h["width"])
    print("  .JPG: %u" % l1i["width"])
    print("height")
    print("  HTML: %u" % l1h["height"])
    print("  .JPG: %u" % l1i["height"])
    """
    if l1h["imageSize"] == l1i["imageSize"]:
        print("Metadata ok, skipping")
        return
    """

    # Base it on the existing data, but tweak as needed
    j_new = copy.deepcopy(j_html)
    l1n = j_new["layers"][0]

    # Fix image pan parameters
    # This is the most visible problem
    l1n["imageSize"] = l1i["imageSize"]
    l1n["width"] = l1i["width"]
    l1n["height"] = l1i["height"]

    # Some old metadata not needed anymore
    if "name_raw" in j_new:
        print("Deleteing name_raw: %s" % j_new["name_raw"])
        del j_new["name_raw"]
    """
    Move copyright from top to layer
    initViewer({"tilesAlignedTopLeft": true, "scale": null, "layers":
        [{"imageSize": 32000, "tileExt": ".jpg", "width": 18393, "height": 13492, "URL": "l1", "tileSize": 250, "name": "ti_tms9918an_mz_mit20x, &copy; 2020 John McMaster, CC-BY"}],
        "name": "???", "name_raw": "None", "copyright": "&copy; 2020 John McMaster, CC-BY"});
    """
    if "copyright" in j_new:
        if "copyright" in l1n:
            raise Exception("FIXME: might be overwriting copyright info")
        # "copyright": "&copy; 2020 John McMaster, CC-BY"
        copyright = j_new["copyright"]
        copyright = copyright.replace("&copy; ", "")
        l1n["copyright"] = copyright
        del j_new["copyright"]

    if j_new["name"] == "???":
        new_name = l1i["name"]
        print("New layer name: %s" % new_name)
        j_new["name"] = new_name
        l1n["name"] = new_name

    # Fix copyright string in name
    # I believe this was transitional hack before GroupXIV added this natively
    # It seems these also have "copyright" set, so just need to trim out extra
    # 'name': 'out, &copy;2018 John McMaster, CC BY'
    if "&copy;" in j_new["name"]:
        if "copyright" not in l1n:
            raise Exception("FIXME: might be losing copyright info")
        # A lot of the names here are just "out"
        new_name = l1i["name"]
        print("New layer name: %s" % new_name)
        j_new["name"] = new_name
        l1n["name"] = new_name

    print("")
    print("final")
    print(j_new)

    if dry:
        print("dry: omitting write")
    else:
        shift_existing_fn(html_fn)
        write_js_meta(html_fn, j_new)


def add_bool_arg(parser, yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg,
                        dest=dest,
                        action='store_true',
                        default=default,
                        **kwargs)
    parser.add_argument('--no-' + dashed,
                        dest=dest,
                        action='store_false',
                        **kwargs)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--verbose",
                        action="store_true",
                        help="Verbose output")
    parser.add_argument("--dry", action="store_true", help="Don't write")
    parser.add_argument("map_dir")
    args = parser.parse_args()
    run(map_dir=args.map_dir, dry=args.dry, verbose=args.verbose)


if __name__ == "__main__":
    main()
