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

import img2doku
from img2doku import parse_image_name, validate_username

STATUS_DONE = "Done"
STATUS_PENDING = "Pending"
STATUS_ERROR = "Error"
STATUS_COLLISION = "Collision"

WWW_DIR = None
LO_SCRAPE_DIRS = None
WIKI_NS_DIR = None
WIKI_DIR = None

def setup_env(dev=False, remote=False):
    global WWW_DIR
    # Directory containing high resolution maps
    global MAP_DIR
    global WIKI_DIR
    # Directory containing simapper pages
    global WIKI_NS_DIR
    # File holding manual import table
    global WIKI_PAGE
    # List of directories to look for high resolution images
    # Must be in a sub-directory with the user that wants to import it
    global HI_SCRAPE_DIRS
    global LO_SCRAPE_DIRS

    # Production
    WWW_DIR = "/var/www"
    # Production debugged remotely
    # discouraged, used for intiial testing mostly
    if remote:
        WWW_DIR = "/mnt/si/var/www"
    # Local development
    if dev:
        WWW_DIR = os.getcwd() + "/dev"
    assert os.path.exists(WWW_DIR), "Failed to find " + WWW_DIR

    MAP_DIR = WWW_DIR + "/map"
    assert os.path.exists(MAP_DIR), MAP_DIR
    WIKI_DIR = WWW_DIR + "/archive"
    WIKI_NS_DIR = WWW_DIR + "/archive/data/pages/simapper"
    assert os.path.exists(WIKI_NS_DIR), WIKI_NS_DIR
    WIKI_PAGE = WIKI_NS_DIR + "/start.txt"
    assert os.path.exists(WIKI_PAGE), WIKI_PAGE
    # TODO: consider SFTP bridge
    HI_SCRAPE_DIRS = [WWW_DIR + "/uploadtmp/simapper"]
    for d in HI_SCRAPE_DIRS:
        assert os.path.exists(d), d
    LO_SCRAPE_DIRS = [WWW_DIR + "/uploadtmp/sipager"]
    for d in HI_SCRAPE_DIRS:
        assert os.path.exists(d), d
    # TODO: create a way to quickly import low resolution images
    # Add the image directly to the page

    print_log_break()
    print("Environment:")
    print("  WWW_DIR: ", WWW_DIR)
    print("  MAP_DIR: ", MAP_DIR)
    print("  WIKI_PAGE: ", WIKI_PAGE)
    print("  HI_SCRAPE_DIRS: ", HI_SCRAPE_DIRS)

def get_user_page(user):
    return WIKI_NS_DIR + "/" + user + ".txt"

def parse_page(page):
    header = ""
    entries = []

    f = open(page)

    # Find table entry
    for l in f:
        if l.strip() == "====== Table ======":
            break
        header += l
    else:
        raise ValueError("Failed to find table sync")

    # Check table entries
    for l in f:
        l = l.strip()
        if not l:
            continue
        if re.match(r"\^ *User *\^ *URL *\^ *Force name *\^ *Status *\^ *Map *\^ *Wiki *\^ *Notes *\^", l):
            continue
        try:
            _a, user, url, force_name, status, map_, wiki, notes, _b = l.split("|")
        except:
            print("Bad: %s" % l)
            raise
        entries.append({
            "user": user.strip(),
            "url": url.strip(),
            "force_name": force_name.strip(),
            "status": status.strip(),
            "map": map_.strip(),
            "wiki": wiki.strip(),
            "notes": notes.strip(),
        })

    return header, entries


def update_page(page, header, entries=[]):
    buff = ""

    if not header:
        header = """
This page is used to import images into https://siliconpr0n.org/map/

For now only .jpg is supported

See also: https://siliconpr0n.org/lib/simapper.txt
"""
    buff += header

    buff += """\
====== Table ======

^ User ^ URL ^ Force name ^ Status ^ Map ^ Wiki ^ Notes ^
"""
    for entry in entries:
        buff += "| %s | %s | %s | %s | %s | %s | %s |\n" % (entry["user"], entry["url"],
                                             entry["force_name"],
                                             entry["status"], entry["map"],
                                             entry["wiki"], entry["notes"])
    f = open(page + ".tmp", "w")
    f.write(buff)
    f.flush()
    f.close()
    shutil.move(page + ".tmp", page)
    # subprocess.check_call("chgrp www-data %s" % page, shell=True)
    # subprocess.check_call("chown www-data %s" % page, shell=True)

def log_simapper_update(entry):
    """
    Update user page w/ URL
    """
    page = get_user_page(entry["user"])
    print("Adding link to " + page)
    f = open(page, "a")
    try:
        # Double new line to put links on individual lines
        f.write("\n")
        f.write("[[" + entry["wiki"] + "]]\n")
        f.flush()
    finally:
        f.close()

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
    print("Parsing raw URL: %s" % (url_check,))
    # Patch up case errors server side
    url_check = url_check.lower()
    # Allow query strings at end (ex: for filebin)
    url_check = url_check.split("?")[0]
    print("Parsing simplified URL: %s" % (url_check,))
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
        MAP_DIR,
        vendor,
    )
    chipid_dir = MAP_DIR + "/" + vendor + "/" + chipid
    single_dir = MAP_DIR + "/" + vendor + "/" + chipid + "/single"
    single_fn = MAP_DIR + "/" + vendor + "/" + chipid + "/single/" + fnbase
    map_fn = MAP_DIR + "/%s/%s/%s" % (vendor, chipid, flavor)
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
        print(subprocess.check_output(["identify", single_fn]))
        print("Sanity check OK")

        print("Converting...")
        try:
            map_user.run(user=entry["user"], files=[single_fn], run_img2doku=False)
        except:
            print("Conversion failed")
            traceback.print_exc()
            entry["status"] = STATUS_ERROR
            return

        _out_txt, wiki_page, wiki_url, map_chipid_url, wrote, exists = img2doku.run(
            fns=[single_fn], collect=entry["user"], write=True, write_lazy=True,
            www_dir=WWW_DIR)
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

def scrape_wiki_page():
    changed = False
    try:
        header, entries = parse_page(WIKI_PAGE)
    except:
        print("")
        print("")
        print("")
        print("Failed to parse")
        print(open(WIKI_PAGE, "r").read())
        print("")
        print("")
        print("")
        raise

    # Spams log too much
    # print("Parsed @ %s" % (datetime.datetime.utcnow().isoformat(), ))
    for entry in entries:
        if not (entry["status"] == ""
                or entry["status"] == STATUS_PENDING):
            continue
        print_log_break()
        changed = True
        entry["status"] = STATUS_PENDING
        update_page(WIKI_PAGE, header, entries)
        try:
            process(entry)
        except Exception as e:
            if not user_dir in warned_wiki_page:
                print("WARNING: exception: %s" % (e, ))
                traceback.print_exc()
            entry["status"] = STATUS_ERROR
            update_page(WIKI_PAGE, header, entries)
            warned_wiki_page.add(user_dir)

    if changed:
        update_page(WIKI_PAGE, header, entries)

def mk_entry(status="", user=None, force_name=None, url=None, local_fn=None):
    assert user
    ret = {"user": user, "status": status}
    if force_name:
        ret["force_name"] = force_name
    if  url:
        ret["url"] = url
    if local_fn:
        ret["local_fn"] = local_fn
    return ret

def print_log_break():
    for _ in range(6):
        print("")
    print("*" * 78)

tried_upload_files = set()

def scrape_upload_dir(once=False, verbose=False):
    """
    TODO: consider implementing upload timeout
    As currently implemented dokuwiki buffers files and writes them instantly
    However might want to allow slower uploads such as through sftp
    Consider verifying the file size is stable (say over 1 second)
    """
    # verbose = True
    verbose and print("")
    verbose and print("Scraping upload dir")
    for scrape_dir in HI_SCRAPE_DIRS:
        for user_dir in glob.glob(scrape_dir + "/*"):
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
                    # Ignore upload dir
                    if not os.path.isfile(im_fn):
                        verbose and print("Not a file " + im_fn)
                        continue
                    print_log_break()
                    print("Found fn: " + im_fn)
                    process(mk_entry(user=user, local_fn=im_fn))
            except Exception as e:
                print("WARNING: exception scraping user dir: %s" % (e, ))
                if once:
                    raise
                else:
                    traceback.print_exc()


def run(once=False, dev=False, remote=False):
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
            scrape_wiki_page()
        except Exception as e:
            print("WARNING: exception: %s" % (e, ))
            if once:
                raise
            else:
                traceback.print_exc()

        try:
            scrape_upload_dir(once=once)
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
    parser.add_argument('--dev',
                        action="store_true",
                        help='Local test')
    parser.add_argument('--remote',
                        action="store_true",
                        help='Remote test')
    parser.add_argument('--once',
                        action="store_true",
                        help='Test once and exit')
    args = parser.parse_args()

    run(dev=args.dev, remote=args.remote, once=args.once)


if __name__ == "__main__":
    main()
