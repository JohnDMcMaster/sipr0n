#!/usr/bin/env python3

import re
import os
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
import env

import img2doku
from img2doku import parse_image_name, validate_username

STATUS_DONE = "Done"
STATUS_PENDING = "Pending"
STATUS_ERROR = "Error"
STATUS_COLLISION = "Collision"


def get_user_page(user):
    return env.SIMAPPER_USER_DIR + "/" + user + ".txt"


def log_simapper_update(entry, page=None):
    """
    Update user page w/ URL
    """
    if page is None:
        page = get_user_page(entry["user"])

    print("Adding link to " + page)

    page_dir = os.path.dirname(page)
    if not os.path.exists(page_dir):
        print("mkdir " + page_dir)
        os.mkdir(page_dir)

    f = open(page, "a")
    try:
        # Double new line to put links on individual lines
        f.write("\n")
        f.write("[[" + entry["wiki"] + "]]\n")
        f.flush()
    finally:
        f.close()

    # Force cache update
    # Works from chrome but not wget
    # subprocess.check_call(["wget", "-O", "/dev/null", entry["wiki"]])


def reindex_all(dev=False):
    print("Running reindex all")
    # subprocess.check_call("sudo -u www-data php /var/www/archive/bin/indexer.php", shell=True)
    # Already running as www-data
    if dev:
        print("dev: skip reindex")
    else:
        subprocess.check_output("php /var/www/archive/bin/indexer.php",
                                shell=True)
    print("Reindex complete")


def shift_done(entry):
    done_dir = os.path.dirname(entry["local_fn"]) + "/done"
    if not os.path.exists(done_dir):
        os.mkdir(done_dir)
    dst_fn = done_dir + "/" + os.path.basename(entry["local_fn"])
    print("Archiving local file %s => %s" % (entry["local_fn"], dst_fn))
    shutil.move(entry["local_fn"], dst_fn)


def process(entry):
    print("")
    print(entry)
    print("Validating URL file name...")
    source_fn = entry.get("local_fn") or entry["url"]
    url_check = entry.get("force_name") or source_fn
    print("Parsing raw URL: %s" % (url_check, ))
    # Patch up case errors server side
    url_check = url_check.lower()
    # Allow query strings at end (ex: for filebin)
    url_check = url_check.split("?")[0]
    print("Parsing simplified URL: %s" % (url_check, ))
    fnbase, vendor, chipid, flavor = parse_image_name(url_check)

    if not validate_username(entry["user"]):
        print("Invalid user name: %s" % entry["user"])
        entry["status"] = STATUS_ERROR
        return
    """
    script_fn = "/home/mcmaster/bin/map-%s" % entry["user"]
    if not os.path.exists(script_fn):
        print("Import script not found: %s" % script_fn)
        entry["status"] = STATUS_ERROR
        return
    """

    print("Checking if exists..")
    vendor_dir = "%s/%s/" % (
        env.MAP_DIR,
        vendor,
    )
    chipid_dir = env.MAP_DIR + "/" + vendor + "/" + chipid
    single_dir = env.MAP_DIR + "/" + vendor + "/" + chipid + "/single"
    single_fn = env.MAP_DIR + "/" + vendor + "/" + chipid + "/single/" + fnbase
    map_fn = env.MAP_DIR + "/%s/%s/%s" % (vendor, chipid, flavor)
    print("Checking %s...." % single_fn)
    if os.path.exists(single_fn):
        print("Collision (single): %s" % single_fn)
        entry["status"] = STATUS_COLLISION
        return
    print("Checking %s...." % map_fn)
    if os.path.exists(map_fn):
        print("Collision (map): %s" % map_fn)
        entry["status"] = STATUS_COLLISION
        return

    def cleanup():
        if os.path.exists(single_fn):
            print("WARNING: deleting map image failure: " + single_fn)
            os.unlink(single_fn)
        if os.path.exists(map_fn):
            print("WARNING: deleting map dir on failure: " + map_fn)
            shutil.rmtree(map_fn)

    try:
        print("Checking if directories exist....")
        if not os.path.exists(vendor_dir):
            print("Create %s" % vendor_dir)
            os.mkdir(vendor_dir)
        if not os.path.exists(chipid_dir):
            print("Create %s" % chipid_dir)
            os.mkdir(chipid_dir)
        if not os.path.exists(single_dir):
            print("Create %s" % single_dir)
            os.mkdir(single_dir)

        print("Fetching file...")
        if "local_fn" in entry:
            print("Local copy %s => %s" % (entry["local_fn"], single_fn))
            shutil.copy(entry["local_fn"], single_fn)
        else:
            print("Downloading %s => %s" % (entry["url"], single_fn))
            with urllib.request.urlopen(entry["url"]) as response:
                # Note: this fixes case issue as we explicitly set output case lower
                ftmp = open(single_fn, "wb")
                shutil.copyfileobj(response, ftmp)
                ftmp.close()

        # Sanity check its image file / multimedia
        # Mostly intended for failing faster on HTML in non-direct link
        subprocess.check_call(["identify", single_fn])
        print("Sanity check OK")

        print("Converting...")
        try:
            map_user.run(user=entry["user"],
                         files=[single_fn],
                         run_img2doku=False)
        except:
            print("Conversion failed")
            traceback.print_exc()
            entry["status"] = STATUS_ERROR
            return

        _out_txt, wiki_page, wiki_url, map_chipid_url, wrote, exists = img2doku.run(
            hi_fns=[single_fn],
            collect=entry["user"],
            write=True,
            write_lazy=True,
            www_dir=env.WWW_DIR)
        print("wiki_page: " + wiki_page)
        print("wiki_url: " + wiki_url)
        print("map_chipid_url: " + map_chipid_url)
        print("wrote: " + str(wrote))
        print("exists: " + str(exists))
        entry["map"] = map_chipid_url
        entry["wiki"] = wiki_url
        log_simapper_update(entry)

        if "local_fn" in entry:
            shift_done(entry)
        entry["status"] = STATUS_DONE
    finally:
        if entry["status"] != STATUS_DONE:
            print("Cleaning up on non-sucess")
            cleanup()


warned_wiki_page = set()


def mk_entry(status="", user=None, force_name=None, url=None, local_fn=None):
    assert user
    ret = {"user": user, "status": status}
    if force_name:
        ret["force_name"] = force_name
    if url:
        ret["url"] = url
    if local_fn:
        ret["local_fn"] = local_fn
    return ret


def print_log_break():
    for _ in range(6):
        print("")
    print("*" * 78)


tried_upload_files = set()


def scrape_upload_dir(once=False, dev=False, verbose=False):
    """
    TODO: consider implementing upload timeout
    As currently implemented dokuwiki buffers files and writes them instantly
    However might want to allow slower uploads such as through sftp
    Consider verifying the file size is stable (say over 1 second)
    """
    # verbose = True
    verbose and print("")
    verbose and print("Scraping upload dir")
    change = False
    for user_dir in glob.glob(env.SIMAPPER_DIR + "/*"):
        if user_dir in tried_upload_files:
            verbose and print("Ignoring tried: " + user_dir)
            continue

        try:
            if not os.path.isdir(user_dir):
                verbose and print("Ignoring not a dir: " + user_dir)
                tried_upload_files.add(user_dir)
                raise Exception("unexpected file " + user_dir)
            user = os.path.basename(user_dir)
            verbose and print("Checking user dir " + user_dir)
            for im_fn in glob.glob(user_dir + "/*"):
                if im_fn in tried_upload_files:
                    verbose and print("Already tried: " + im_fn)
                    continue
                tried_upload_files.add(im_fn)
                # Ignore done dir
                if not os.path.isfile(im_fn):
                    verbose and print("Not a file " + im_fn)
                    continue
                print_log_break()
                print("Found fn: " + im_fn)
                process(mk_entry(user=user, local_fn=im_fn))
                change = True
        except Exception as e:
            print("WARNING: exception scraping user dir: %s" % (e, ))
            if once:
                raise
            else:
                traceback.print_exc()
    if change:
        reindex_all(dev=dev)


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
            scrape_upload_dir(once=once, dev=dev)
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
    args = parser.parse_args()

    run(dev=args.dev, remote=args.remote, once=args.once)


if __name__ == "__main__":
    main()
