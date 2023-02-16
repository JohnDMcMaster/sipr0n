#!/usr/bin/env python3

import os
import glob
import shutil
import subprocess
import time
import traceback
import map_user
from sipr0n import env
from sipr0n.util import FnRetry
from sipr0n import simap
import json

import img2doku
from sipr0n.util import parse_map_image_user_vcufe, validate_username, map_image_uvcfe_to_basename

STATUS_DONE = "Done"
STATUS_PENDING = "Pending"
STATUS_ERROR = "Error"
STATUS_COLLISION = "Collision"

fn_retry = FnRetry()


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
    vendor, chipid, user, flavor, ext = parse_map_image_user_vcufe(
        entry["local_fn"], assume_user=entry["user"])
    dst_basename = map_image_uvcfe_to_basename(vendor, chipid, user, flavor,
                                               ext)

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
    single_fn = env.MAP_DIR + "/" + vendor + "/" + chipid + "/single/" + dst_basename
    map_fn = env.MAP_DIR + "/%s/%s/%s_%s" % (vendor, chipid, user, flavor)
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
        print("Local copy %s => %s" % (entry["local_fn"], single_fn))
        shutil.copy(entry["local_fn"], single_fn)
        single_rel = "single/" + os.path.basename(single_fn)
        simap.map_manifest_add_file(basedir=chipid_dir,
                                    fn=single_rel,
                                    collection=user,
                                    type_="image")

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

        map_rel = os.path.basename(map_chipid_url)
        simap.map_manifest_add_file(basedir=chipid_dir,
                                    fn=map_rel,
                                    collection=user,
                                    type_="map")

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
    for _i in range(6):
        print("")
    print("*" * 78)


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
        user_dir = os.path.realpath(user_dir)
        if not fn_retry.should_try_fn(user_dir):
            verbose and print("Ignoring tried: " + user_dir)
            continue

        try:
            if not os.path.isdir(user_dir):
                verbose and print("Ignoring not a dir: " + user_dir)
                fn_retry.blacklist_fn(user_dir)
                raise Exception("unexpected file " + user_dir)
            user = os.path.basename(user_dir)
            verbose and print("Checking user dir " + user_dir)
            for im_fn in glob.glob(user_dir + "/*"):
                im_fn = os.path.realpath(im_fn)
                if not fn_retry.try_fn(im_fn):
                    verbose and print("Already tried: " + im_fn)
                    continue
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

    shutil.rmtree(env.SIMAPPER_TMP_DIR, ignore_errors=True)
    os.mkdir(env.SIMAPPER_TMP_DIR)

    try:
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
    finally:
        shutil.rmtree(env.SIMAPPER_TMP_DIR, ignore_errors=True)


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