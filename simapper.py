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

from img2doku import parse_image_name

STATUS_DONE = "Done"
STATUS_PENDING = "Pending"
STATUS_ERROR = "Error"
STATUS_COLLISION = "Collision"

MAP_DIR = "/var/www/map"
if os.path.exists("/mnt/si"):
    MAP_DIR = "/mnt/si" + MAP_DIR


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
        if re.match(r"\^ *User *\^ *URL *\^ *Status *\^ *Map *\^ *Wiki *\^ *Notes *\^", l):
            continue
        try:
            _a, user, url, status, map_, wiki, notes, _b = l.split("|")
        except:
            print("Bad: %s" % l)
            raise
        entries.append({
            "user": user.strip(),
            "url": url.strip(),
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

^ User ^ URL ^ Status ^ Map ^ Wiki ^ Notes ^
"""
    for entry in entries:
        buff += "| %s | %s | %s | %s | %s | %s |\n" % (entry["user"], entry["url"],
                                             entry["status"], entry["map"],
                                             entry["wiki"], entry["notes"])
    f = open(page + ".tmp", "w")
    f.write(buff)
    f.flush()
    f.close()
    shutil.move(page + ".tmp", page)
    # subprocess.check_call("chgrp www-data %s" % page, shell=True)
    # subprocess.check_call("chown www-data %s" % page, shell=True)


def process(entry):
    print("")
    print(entry)
    print("Validating URL file name...")
    url_check = entry["url"]
    print("Parsing raw URL: %s" % (url_check,))
    # Patch up case errors server side
    url_check = url_check.lower()
    # Allow query strings at end (ex: for filebin)
    url_check = url_check.split("?")[0]
    print("Parsing simplified URL: %s" % (url_check,))
    fnbase, vendor, chipid, flavor = parse_image_name(url_check)

    if not re.match("[a-z]+", entry["user"]):
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
    with urllib.request.urlopen(entry["url"]) as response:
        # Note: this fixes case issue as we explicitly set output case lower
        ftmp = open(single_fn, "wb")
        shutil.copyfileobj(response, ftmp)
        ftmp.close()
    """
    with urllib.request.urlopen('http://www.example.com/') as f:
        open(single_fn, "wb").write(f.read())
    """

    print("Converting...")
    """
    try:
        # Scary
        subprocess.check_call("cd '%s' && '%s' '%s'" %
                              (chipid_dir, script_fn, single_fn),
                              shell=True)
    except:
        print("Conversion failed")
        entry["status"] = STATUS_ERROR
        return
    """
    try:
        _wiki_page, wiki_url, map_chipid_url = map_user.run(user=entry["user"], files=[single_fn])
        entry["map"] = map_chipid_url
        entry["wiki"] = wiki_url
    except:
        print("Conversion failed")
        traceback.print_exc()
        entry["status"] = STATUS_ERROR
        return

    entry["status"] = STATUS_DONE


def run(page, once=False):
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
        changed = False
        try:
            try:
                header, entries = parse_page(page)
            except:
                print("")
                print("")
                print("")
                print("Failed to parse")
                print(open(page, "r").read())
                print("")
                print("")
                print("")
                raise
                continue

            print("Parsed @ %s" % (datetime.datetime.utcnow().isoformat(), ))
            for entry in entries:
                if not (entry["status"] == ""
                        or entry["status"] == STATUS_PENDING):
                    continue
                changed = True
                entry["status"] = STATUS_PENDING
                update_page(page, header, entries)
                process(entry)

            if changed:
                update_page(page, header, entries)
        except Exception as e:
            print("WARNING: exception: %s" % (e, ))
            traceback.print_exc()
            pass


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitor for sipr0n map imports')
    parser.add_argument('--page',
                        default="/var/www/archive/data/pages/simapper.txt",
                        help='Page to monitor')
    # parser.add_argument('--log', default="/var/www/lib/simapper.txt", help='Log file')
    args = parser.parse_args()

    run(page=args.page)


if __name__ == "__main__":
    main()
