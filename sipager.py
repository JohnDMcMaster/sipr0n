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
from img2doku import parse_vendor_chipid_name, validate_username
import simapper
from simapper import print_log_break, setup_env, STATUS_DONE

def shift_done(entry):
    done_dir = os.path.dirname(entry["local_fn"]) + "/done"
    if not os.path.exists(done_dir):
        os.mkdir(done_dir)
    dst_fn = done_dir + "/" + os.path.basename(entry["local_fn"])
    print("Archiving local file %s => %s" % (entry["local_fn"], dst_fn))
    shutil.move(entry["local_fn"], dst_fn)

def find_txt(entry):
    txts = glob.glob(entry["local_fn"] + "/*.txt")
    if len(txts) == 0:
        return None
    if len(txts) > 1:
        raise Exception("Too many .txt files")
    return open(txts[0], "r").read()

def find_lo_fns(entry):
    return list(glob.glob(entry["local_fn"] + "/*.jpg"))

def get_user_page(user):
    return simapper.WIKI_NS_DIR + "/" + user + "/sipager.txt"

def log_sipager_update(entry):
    """
    Update user page w/ URL
    """
    page = get_user_page(entry["user"])

    page_dir = os.path.dirname(page)
    if not os.path.exists(page_dir):
        print("mkdir " + page_dir)
        os.mkdir(page_dir)

    print("Adding link to " + page)
    f = open(page, "a")
    try:
        # Double new line to put links on individual lines
        f.write("\n")
        f.write("[[" + entry["wiki"] + "]]\n")
        f.flush()
    finally:
        f.close()

def process(entry):
    print("")
    print(entry)
    if not os.path.isdir(entry["local_fn"]):
        raise Exception("Only dir import supported at this time")

    url_check = entry["local_fn"]
    url_check = url_check.lower()
    # Just validate, don't actually need?
    _fnbase, vendor, chipid = parse_vendor_chipid_name(url_check)

    if not validate_username(entry["user"]):
        print("Invalid user name: %s" % entry["user"])
        return

    # Optional
    # Output as code text for now
    # maybe allow "wiki.txt" for direct wiki text input without code escape
    code_txt = find_txt(entry)

    try:
        page_fns = find_lo_fns(entry)
        for src_fn in page_fns:
            bn = os.path.basename(src_fn)
            print("Importing " + bn)
            if bn not in ("die.jpg", "pack_top.jpg", "pack_btm.jpg"):
                raise Exception("FIXME: non-standard import file name: " % bn)
            vendor_dir = simapper.WIKI_DIR + "/data/media/" + entry["user"] + "/" + vendor
            if not os.path.exists(vendor_dir):
                print("mkdir " + vendor_dir)
                os.mkdir(vendor_dir)
            chipid_dir = vendor_dir + "/" + chipid
            if not os.path.exists(chipid_dir):
                print("mkdir " + chipid_dir)
                os.mkdir(chipid_dir)
            dst_fn = chipid_dir + "/" + bn
            print("cp: " + src_fn + " => " + dst_fn)
            if os.path.exists(dst_fn):
                print("WARNING: overwriting file")
            shutil.copy(src_fn, dst_fn)

        _out_txt, wiki_page, wiki_url, _map_chipid_url, wrote, exists = img2doku.run(
            hi_fns=[], collect=entry["user"], write=True, write_lazy=True,
            www_dir=simapper.WWW_DIR, code_txt=code_txt,
            vendor=vendor, chipid=chipid, page_fns=page_fns)
        print("wiki_page: " + wiki_page)
        print("wiki_url: " + wiki_url)
        print("wrote: " + str(wrote))
        print("exists: " + str(exists))
        entry["wiki"] = wiki_url
        log_sipager_update(entry)

        shift_done(entry)
        entry["status"] = STATUS_DONE
    finally:
        if entry.get("status") != STATUS_DONE:
            print("Cleaning up on non-sucess")
            # Hmm difficult to delete the page if we mess up
            # cleanup()


def mk_entry(status="", user=None, local_fn=None):
    assert user
    assert local_fn
    ret = {"user": user, "local_fn": local_fn}
    if status:
        ret["status"] = status
    return ret

tried_upload_files = set()

def scrape_upload_dir(once=False, verbose=False):
    """
    TODO: consider implementing upload timeout
    As currently implemented dokuwiki buffers files and writes them instantly
    However might want to allow slower uploads such as through sftp
    Consider verifying the file size is stable (say over 1 second)
    """
    verbose = True
    verbose and print("")
    verbose and print("Scraping upload dir")
    for scrape_dir in simapper.LO_SCRAPE_DIRS:
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
                for user_fn in glob.glob(user_dir + "/*"):
                    if user_fn in tried_upload_files:
                        verbose and print("Already tried: " + user_fn)
                        continue
                    tried_upload_files.add(user_fn)
                    if os.path.basename(user_fn) == "done":
                        continue
                    # TODO: consider single fn or tarball support
                    if not os.path.isdir(user_fn):
                        verbose and print("Not a dir " + user_fn)
                        continue
                    print_log_break()
                    print("Found fn: " + user_fn)
                    process(mk_entry(user=user, local_fn=user_fn))
            except Exception as e:
                print("WARNING: exception scraping user dir: %s" % (e, ))
                if once:
                    raise
                else:
                    traceback.print_exc()


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
    parser.add_argument('--dev',
                        action="store_true",
                        help='Local test')
    parser.add_argument('--remote',
                        action="store_true",
                        help='Remote test')
    parser.add_argument('--once',
                        action="store_true",
                        help='Test once and exit')
    parser.add_argument('--verbose',
                        action="store_true",
                        help='Verbose')
    args = parser.parse_args()

    run(dev=args.dev, remote=args.remote, once=args.once)


if __name__ == "__main__":
    main()
