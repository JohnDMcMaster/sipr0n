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

import os.path
import glob
import shutil
import time
import traceback
import tarfile

import img2doku
from util import parse_vendor_chipid_flavor, parse_user_vendor_chipid_flavor, ParseError
import simapper
from simapper import print_log_break
from util import validate_username
import env


def shift_done(page):
    def archive_images(images):
        for src_fn in images.keys():
            file_completed(src_fn)

    archive_images(page["images"]["header"])
    archive_images(page["images"]["package"])
    archive_images(page["images"]["die"])


def get_user_page(user):
    return env.SIPAGER_USER_DIR + "/" + user + ".txt"


def log_sipager_update(page_name, user):
    simapper.log_simapper_update({"wiki": page_name}, page=get_user_page(user))


def import_images(page):
    print("Importing images...")

    for imagek in ("header", "package", "die"):
        print("Set %s: %u items" % (imagek, len(page["images"][imagek])))
        for src_fn, page_fn in page["images"][imagek].items():
            print("  " + src_fn + " => " + page_fn)

            user_dir = env.ARCHIVE_WIKI_DIR + "/data/media/" + page["user"]
            if not os.path.exists(user_dir):
                print("    mkdir " + user_dir)
                os.mkdir(user_dir)
            vendor_dir = user_dir + "/" + page["vendor"]
            if not os.path.exists(vendor_dir):
                print("    mkdir " + vendor_dir)
                os.mkdir(vendor_dir)
            chipid_dir = vendor_dir + "/" + page["chipid"]
            if not os.path.exists(chipid_dir):
                print("    mkdir " + chipid_dir)
                os.mkdir(chipid_dir)
            dst_fn = chipid_dir + "/" + page_fn
            print("    cp: " + src_fn + " => " + dst_fn)
            if os.path.exists(dst_fn):
                print("    WARNING: overwriting file")
            shutil.copy(src_fn, dst_fn)
    print("")


def process(page):
    print_log_break()
    print("Generating %s" % (page["page"], ))

    import_images(page)
    """
    convert canonical.jpg: wiki.jpg to just wiki.jpg

    Also should consider ordering pack_top.jpg before pack_btm.jpg
    """
    package_images = sorted(list(page["images"]["package"].values()))
    # If "pack_top." is found push to front
    # "pack_btm." should be second
    # XXX: only solve trivial case right now of two images
    # swap if we don't like the order
    if len(package_images) > 1 and package_images[1] == "pack_top.jpg":
        package_images[0], package_images[1] = package_images[
            1], package_images[0]

    force_fns = {
        "header": sorted(list(page["images"]["header"].values())),
        "package": package_images,
        "die": sorted(list(page["images"]["die"].values())),
    }

    _out_txt, wiki_page, wiki_url, _map_chipid_url, wrote, exists = img2doku.run(
        hi_fns=[],
        collect=page["user"],
        write=True,
        write_lazy=True,
        www_dir=env.WWW_DIR,
        vendor=page["vendor"],
        chipid=page["chipid"],
        page_fns=None,
        force_tags=page["tags"],
        force_fns=force_fns,
    )
    print("wiki_page: " + wiki_page)
    print("wiki_url: " + wiki_url)
    print("wrote: " + str(wrote))
    print("exists: " + str(exists))
    log_sipager_update(wiki_url, page["user"])

    shift_done(page)


failed_upload_files = set()


def file_completed(src_fn):
    """
    Archive a file that was completed
    """

    done_dir = os.path.dirname(src_fn) + "/done"
    if not os.path.exists(done_dir):
        os.mkdir(done_dir)
    dst_fn = done_dir + "/" + os.path.basename(src_fn)
    print("Archiving local file %s => %s" % (src_fn, dst_fn))
    shutil.move(src_fn, dst_fn)


def extract_archives(scrape_dir, assume_user):
    """
    Extract archives into current dir

    Rules:
    -File paths ignored / flattened
    -Only approved image extensions?
    """
    def conforming_name(fn):
        try:
            _parsed = parse_assume_user(fn, assume_user=assume_user)
        except ParseError:
            return False
        return True

    for fn_glob in glob.glob(scrape_dir + "/*.tar"):
        tar = tarfile.open(fn_glob, "r")
        print("tar: examining %s" % (fn_glob, ))
        try:
            for tarinfo in tar:
                if not tarinfo.isreg():
                    if not tarinfo.isdir():
                        print("  WARNING: unrecognized tar element: %s" %
                              (str(tarinfo), ))
                    continue

                basename = os.path.basename(tarinfo.name).lower()
                if not conforming_name(basename):
                    print("  WARNING: bad image file name within archive: %s" %
                          (tarinfo.name, ))
                    continue

                fn_out = scrape_dir + "/" + basename
                with open(fn_out, "wb") as f:
                    print("  writing %s" % (fn_out))
                    f.write(tar.extractfile(tarinfo).read())

            # Extracted: trash it
            file_completed(fn_glob)
        finally:
            tar.close()


def parse_assume_user(fn_can, assume_user):
    if assume_user:
        parsed = parse_vendor_chipid_flavor(fn_can)
        basename, vendor, chipid, flavor, ext = parsed
        user = assume_user
    else:
        parsed = parse_user_vendor_chipid_flavor(fn_can)
        basename, user, vendor, chipid, flavor, ext = parsed
    return (basename, user, vendor, chipid, flavor, ext)


def bucket_image_dir(scrape_dir, assume_user=None, verbose=False):
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
        if basename == "done" or os.path.isdir(fn_can):
            continue
        verbose and print("Checking file " + fn_can)
        try:
            basename, user, vendor, chipid, flavor, ext = parse_assume_user(
                fn_can.lower(), assume_user)
        except ParseError:
            print("Bad image file name: %s" % (fn_can, ))
            failed_upload_files.add(fn_can)
            continue
        k = "%s:%s:%s" % (user, vendor, chipid)
        print("Parsed %s => %s" % (fn_can, k))
        images = ret.setdefault(k, {})
        images[fn_can] = (basename, user, vendor, chipid, flavor, ext)
    return ret


def parse_image_dir(scrape_dir, assume_user=None, verbose=False):
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
                                              assume_user=assume_user,
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
        entry["vendor"] = vendor
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


def scrape_upload_dir_inner(scrape_dir, assume_user=None, verbose=False):
    change = False
    # don't assume_user here or will double stack against dir name
    extract_archives(scrape_dir, assume_user=assume_user)
    pages = parse_image_dir(scrape_dir,
                            assume_user=assume_user,
                            verbose=verbose)
    verbose and print_log_break()

    for page in pages.values():
        process(page)
        change = True

    return change


def scrape_upload_dir_outer(verbose=False, dev=False):
    """
    TODO: consider implementing upload timeout
    As currently implemented dokuwiki buffers files and writes them instantly
    However might want to allow slower uploads such as through sftp
    Consider verifying the file size is stable (say over 1 second)
    """
    verbose and print("")
    verbose and print("Scraping upload dir")
    change = False
    # Check main dir with username prefix
    scrape_upload_dir_inner(env.SIPAGER_DIR, verbose=verbose)

    # Check user dirs
    for glob_dir in glob.glob(env.SIPAGER_DIR + "/*"):
        fn_can = os.path.realpath(glob_dir)
        if not os.path.isdir(fn_can):
            continue
        if fn_can in failed_upload_files:
            continue
        basename = os.path.basename(fn_can)
        if basename == "done":
            continue
        user = basename

        if not validate_username(user):
            failed_upload_files.add(fn_can)
            print("Invalid user name: %s" % user)
            continue
        scrape_upload_dir_inner(glob_dir, verbose=verbose, assume_user=user)

    if change:
        simapper.reindex_all(dev=dev)


def run(once=False, dev=False, remote=False, verbose=False):
    env.setup_env(dev=dev, remote=remote)

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
            scrape_upload_dir_outer(verbose=verbose, dev=dev)
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
