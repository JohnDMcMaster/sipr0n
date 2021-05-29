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
    src_fn = entry.get("im_fn", None) or entry.get("dir_fn", None)
    done_dir = os.path.dirname(src_fn) + "/done"
    if not os.path.exists(done_dir):
        os.mkdir(done_dir)
    dst_fn = done_dir + "/" + os.path.basename(src_fn)
    print("Archiving local file %s => %s" % (src_fn, dst_fn))
    shutil.move(src_fn, dst_fn)

def find_txt(entry):
    txts = glob.glob(entry["dir_fn"] + "/*.txt")
    if len(txts) == 0:
        return None
    if len(txts) > 1:
        raise Exception("Too many .txt files")
    return open(txts[0], "r").read()

def get_user_page(user):
    return simapper.WIKI_NS_DIR + "/" + user + "/sipager.txt"

def log_sipager_update(entry):
    simapper.log_simapper_update(entry, page=get_user_page(entry["user"]))

def process(entry):
    print("")
    print(entry)
    im_fn = entry.get("im_fn", None)
    dir_fn = entry.get("dir_fn", None)
    if dir_fn and not os.path.isdir(dir_fn):
        raise Exception("Only dir import supported at this time")

    url_check = dir_fn or im_fn
    url_check = url_check.lower()
    # Just validate, don't actually need?
    _fnbase, vendor, chipid = parse_vendor_chipid_name(url_check)

    if not validate_username(entry["user"]):
        print("Invalid user name: %s" % entry["user"])
        return

    # Optional
    # Output as code text for now
    # maybe allow "wiki.txt" for direct wiki text input without code escape
    if dir_fn:
        code_txt = find_txt(entry)
    else:
        code_txt = None

    try:
        if dir_fn:
            page_fns = list(glob.glob(entry["dir_fn"] + "/*.jpg"))
        else:
            page_fns = [im_fn]

        for src_fn in page_fns:
            bn_src = os.path.basename(src_fn)
            print("Importing " + bn_src)
            if dir_fn:
                bn_dst = bn_src
            else:
                bn_dst = "die.jpg"
            if bn_dst not in ("die.jpg", "pack_top.jpg", "pack_btm.jpg"):
                raise Exception("FIXME: non-standard import file name: " % bn_dst)
            vendor_dir = simapper.WIKI_DIR + "/data/media/" + entry["user"] + "/" + vendor
            if not os.path.exists(vendor_dir):
                print("mkdir " + vendor_dir)
                os.mkdir(vendor_dir)
            chipid_dir = vendor_dir + "/" + chipid
            if not os.path.exists(chipid_dir):
                print("mkdir " + chipid_dir)
                os.mkdir(chipid_dir)
            dst_fn = chipid_dir + "/" + bn_dst
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


def mk_entry(status="", user=None, im_fn=None, dir_fn=None):
    assert user
    ret = {"user": user}
    if status:
        ret["status"] = status
    if im_fn:
        ret["im_fn"] = im_fn
    if dir_fn:
        ret["dir_fn"] = dir_fn
    return ret

tried_upload_files = set()

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
                    if os.path.isdir(user_fn):
                        print_log_break()
                        print("Found dir fn: " + user_fn)
                        process(mk_entry(user=user, dir_fn=user_fn))
                        change = True
                    elif '.jpg' in user_fn:
                        print_log_break()
                        print("Found im fn: " + user_fn)
                        process(mk_entry(user=user, im_fn=user_fn))
                        change = True
                    else:
                        verbose and print("Not a dir " + user_fn)
                        continue
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

    run(dev=args.dev, remote=args.remote, once=args.once, verbose=args.verbose)


if __name__ == "__main__":
    main()
