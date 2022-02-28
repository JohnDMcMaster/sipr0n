#!/usr/bin/env python3
"""
sipager is for rapidly creating pages from image collections


FIXME: MVP doesn't need tar support but needed for reliable operation



Original design
dir would contain stuff for page

new design
images must be canonically named
this makes mass import, tarball, etc easy
Images need to be bucketed into pages

If the page already exists:
Append at end

name images like
$user_$vendor_$product_$suffix
for example
mcmaster_microchip_pic16c57_pack_top.jpg
mcmaster_microchip_pic16c57_die.jpg

Special cases:
-Anything starting with pack* goes into pack section
-Anything starting with die* goes into die section
-Other images will get put at the top
    ex: if you have a PCB or other context


Where should images be buffered?
-Global dir: need user prefix
    more scalable
    ***start with this
-User dir: user name assumed
    more convenient


How to treat archives?
extract them in dir?
weird corner cases like extracting to onelself should be concerned with?
"""

import re
import os
import os.path
import glob
import urllib
import urllib.request
import tempfile
import shutil
import subprocess
import time
import datetime
import traceback
import sys
import map_user
import os

import img2doku
from img2doku import parse_vendor_chipid_name, validate_username, parse_user_vendor_chipid_flavor, ParseError
import simapper
from simapper import print_log_break, setup_env, STATUS_DONE


def shift_done(page):
    def archive_images(images):
        for src_fn in images.keys():
            done_dir = os.path.dirname(src_fn) + "/done"
            if not os.path.exists(done_dir):
                os.mkdir(done_dir)
            dst_fn = done_dir + "/" + os.path.basename(src_fn)
            print("Archiving local file %s => %s" % (src_fn, dst_fn))
            shutil.move(src_fn, dst_fn)

    archive_images(page["images"]["header"])
    archive_images(page["images"]["package"])
    archive_images(page["images"]["die"])


def get_user_page(user):
    return simapper.WIKI_NS_DIR + "/" + user + "/sipager.txt"


def log_sipager_update(page_name, user):
    simapper.log_simapper_update({"wiki": page_name}, page=get_user_page(user))


def import_images(page_fns, page):
    for src_fn, page_fn in page_fns.items():
        print("Importing " + src_fn + " as " + page_fn)

        user_dir = simapper.WIKI_DIR + "/data/media/" + page["user"]
        if not os.path.exists(user_dir):
            print("mkdir " + user_dir)
            os.mkdir(user_dir)
        vendor_dir = user_dir + "/" + page["vendor"]
        if not os.path.exists(vendor_dir):
            print("mkdir " + vendor_dir)
            os.mkdir(vendor_dir)
        chipid_dir = vendor_dir + "/" + page["chipid"]
        if not os.path.exists(chipid_dir):
            print("mkdir " + chipid_dir)
            os.mkdir(chipid_dir)
        dst_fn = chipid_dir + "/" + page_fn
        print("cp: " + src_fn + " => " + dst_fn)
        if os.path.exists(dst_fn):
            print("WARNING: overwriting file")
        shutil.copy(src_fn, dst_fn)


def process(page):
    print("")
    print(page)

    import_images(page["images"]["header"], page)
    import_images(page["images"]["package"], page)
    import_images(page["images"]["die"], page)

    def page_fns():
        """
        convert canonical.jpg: wiki.jpg to just wiki.jpg

        Also should consider ordering pack_top.jpg before pack_btm.jpg
        """
        return {
            "header": list(page["images"]["header"].values()),
            "package": list(page["images"]["package"].values()),
            "die": list(page["images"]["die"].values()),
        }

    _out_txt, wiki_page, wiki_url, _map_chipid_url, wrote, exists = img2doku.run(
        hi_fns=[],
        collect=page["user"],
        write=True,
        write_lazy=True,
        www_dir=simapper.WWW_DIR,
        vendor=page["vendor"],
        chipid=page["chipid"],
        page_fns=None,
        force_tags=page["tags"],
        force_fns=page_fns(),
    )
    print("wiki_page: " + wiki_page)
    print("wiki_url: " + wiki_url)
    print("wrote: " + str(wrote))
    print("exists: " + str(exists))
    log_sipager_update(wiki_url, page["user"])

    shift_done(page)


tried_upload_files = set()


def extract_archives(scrape_dir):
    """
    Extract archives into current dir

    Rules:
    -Only approved image extensions
    -File paths ignored
    """
    pass


def bucket_image_dir(scrape_dir, verbose=False):
    """
    Find all images in dir
    Group them together with images going into the same page 


    {
        "mcmaster:atmel:328p": [
            "/foo/bar/mcmaster_atmel_at328p_die.jpg",
            "/foo/bar/mcmaster_atmel_at328p_pack_top.jpg"
        ]
    }


    or maybe since they are already parsed?

    {
        "mcmaster:atmel:328p": {
            "/foo/bar/mcmaster_atmel_at328p_die.jpg": (parsed...),
            "/foo/bar/mcmaster_atmel_at328p_pack_top.jpg": (parsed...),
        }
    }
    
    """

    ret = {}
    for fn_glob in glob.glob(scrape_dir + "/*"):
        fn_can = os.path.realpath(fn_glob)
        basename = os.path.basename(fn_can)
        if basename == "done" or basename == "tmp":
            continue
        verbose and print("Checking file " + fn_can)
        try:
            parsed = parse_user_vendor_chipid_flavor(fn_can)
        except ParseError:
            print("Bad file name: %s" % (fn_can, ))
            tried_upload_files.add(fn_can)
            continue
        basename, user, vendor, chipid, _flavor, _ext = parsed
        k = "%s:%s:%s" % (user, vendor, chipid)
        images = ret.setdefault(k, {})
        images[fn_can] = parsed
    return ret


def parse_image_dir(scrape_dir, verbose=False):
    """
    Return dict
    {
        "mcmaster:atmel:at328p": {
            "user": "mcmaster",
            "vendor": "atmel",
            "chipid": "at328p",
            "tags": set(
                "collection_mcmaster",
                "vendor_atmel"
            ),
            "images": {
                "header": {
                },
                "package": {
                },
                "die": {
                    //src:dst within page namespace
                    //Canonical paths
                    "/foo/bar/mcmaster_atmel_at328p_die.jpg": "die.jpg"
                }
            }
        }
    }
    """
    ret = {}
    for page_name, images in bucket_image_dir(scrape_dir,
                                              verbose=verbose).items():
        user, vendor, chipid = page_name.split(":")
        entry = {
            "tags": [
                "collection_" + user, "vendor_" + vendor, "type_unknown",
                "year_unknown", "foundry_unknown"
            ],
            "images": {
                "header": {},
                "package": {},
                "die": {},
            }
        }
        entry["page"] = page_name
        entry["user"] = user
        entry["vendor"] = user
        entry["chipid"] = chipid
        for src_image_can, parsed in images.items():
            _basename, parsed_user, parsed_vendor, parsed_chipid, flavor, ext = parsed
            assert parsed_user == user
            assert parsed_vendor == vendor
            assert parsed_chipid == chipid
            dst_basename = flavor + "." + ext
            # Try to guess the section the image should go under
            if flavor.find("die") == 0:
                entry["images"]["die"][src_image_can] = dst_basename
            elif flavor.find("pack") == 0:
                entry["images"]["package"][src_image_can] = dst_basename
            else:
                entry["images"]["header"][src_image_can] = dst_basename
        ret[page_name] = entry
    return ret


def scrape_upload_dir(once=False, verbose=False):
    """
    TODO: consider implementing upload timeout
    As currently implemented dokuwiki buffers files and writes them instantly
    However might want to allow slower uploads such as through sftp
    Consider verifying the file size is stable (say over 1 second)
    """
    verbose and print("")
    verbose and print("Scraping upload dir")
    change = False
    try:
        for scrape_dir in simapper.SIPAGER_DIRS:
            #tmp_dir = os.path.join(scrape_dir, "tmp")
            #shutil.rmtree(tmp_dir)
            #os.mkdir(tmp_dir)
            extract_archives(scrape_dir)
            pages = parse_image_dir(scrape_dir, verbose=verbose)
            print_log_break()

            for page in pages.values():
                process(page)
                change = True

    except Exception as e:
        print("WARNING: exception scraping user dir: %s" % (e, ))
        if once:
            raise
        else:
            traceback.print_exc()
    if change:
        simapper.reindex_all()


def run(once=False, dev=False, remote=False, verbose=False):
    setup_env(dev=dev, remote=remote)

    # assert getpass.getuser() == "www-data"

    # if not os.path.exists(TMP_DIR):
    #    os.mkdir(TMP_DIR)

    print("Running")
    iters = 0
    while True:
        iters += 1
        if iters > 1 and once:
            print("Break on test mode")
            break
        # Consider select() / notify instead
        if iters > 1:
            time.sleep(3)

        try:
            scrape_upload_dir(once=once, verbose=verbose)
        except Exception as e:
            print("WARNING: exception: %s" % (e, ))
            if once:
                raise
            else:
                traceback.print_exc()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitor for sipr0n map imports')
    parser.add_argument('--dev', action="store_true", help='Local test')
    parser.add_argument('--remote', action="store_true", help='Remote test')
    parser.add_argument('--once',
                        action="store_true",
                        help='Test once and exit')
    parser.add_argument('--verbose', action="store_true", help='Verbose')
    args = parser.parse_args()

    run(dev=args.dev, remote=args.remote, once=args.once, verbose=args.verbose)


if __name__ == "__main__":
    main()
