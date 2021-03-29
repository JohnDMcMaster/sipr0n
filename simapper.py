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

from img2doku import parse_image_name

STATUS_DONE = "Done"
STATUS_PENDING = "Pending"
STATUS_ERROR = "Error"
STATUS_COLLISION = "Collision"

def parse_page(page):
    ret = []

    f = open(page)

    # Find table entry
    for l in f:
        l = l.strip()
        if l == "====== Table ======":
            break
    else:
        raise ValueError("Failed to find table sync")

    # Check table entries
    for l in f:
        l = l.strip()
        if not l:
            continue
        if l == "^ User ^ URL ^ Status ^ Notes ^":
            continue
        _a, user, url, status, notes, _b = l.split("|")
        ret.append({
            "user": user.strip(),
            "url": url.strip(),
            "status": status.strip(),
            "notes": notes.strip(),
            })

    return ret

def update_page(page, entries=[]):
    buff = """\
This page is used to import images into https://siliconpr0n.org/map/

For now only .jpg is supported

See also: https://siliconpr0n.org/lib/simapper.txt

====== Table ======

^ User ^ URL ^ Status ^ Notes ^
"""
    for entry in entries:
        buff += "| %s | %s | %s | %s |" % (entry["user"], entry["url"], entry["status"], entry["notes"])
    f = open(page + ".tmp", "w")
    f.write(buff)
    f.flush()
    f.close()
    shutil.move(page + ".tmp", page)
    subprocess.check_call("chgrp www-data %s" % page, shell=True)
    # subprocess.check_call("chown www-data %s" % page, shell=True)

def process(entry):
    print("")
    print(entry)
    print("Validating URL file name...")
    fnbase, vendor, chipid, flavor = parse_image_name(entry["url"])

    if not re.match("[a-z]+", entry["user"]):
        print("Invalid user name: %s" % entry["user"])
        entry["status"] = STATUS_ERROR
        return
    script_fn = "/home/mcmaster/bin/map-%s" % entry["user"]
    if not os.path.exists(script_fn):
        print("Import script not found: %s" % script_fn)
        entry["status"] = STATUS_ERROR
        return

    print("Checking if exists..")
    vendor_dir = "/var/www/map/%s/" % (vendor,)
    chipid_dir = "/var/www/map/%s/%s/" % (vendor, chipid)
    single_dir = "/var/www/map/%s/%s/single/" % (vendor, chipid)
    single_fn = "/var/www/map/%s/%s/single/%s" % (vendor, chipid, fnbase)
    map_fn = "/var/www/map/%s/%s/%s" % (vendor, chipid, flavor)
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
        ftmp = open(single_fn, "wb")
        shutil.copyfileobj(response, ftmp)
        ftmp.close()
    """
    with urllib.request.urlopen('http://www.example.com/') as f:
        open(single_fn, "wb").write(f.read())
    """

    print("Converting...")
    try:
        # Scary
        subprocess.check_call("cd %s && %s %s" % (chipid_dir, script_fn, single_fn), shell=True)
    except:
        print("Conversion failed")
        entry["status"] = STATUS_ERROR
        return

    entry["status"] = STATUS_DONE

def run(page):
    if not os.path.exists("/tmp/simapper"):
        os.mkdir("/tmp/simapper")

    print("Running")
    while True:
        time.sleep(3)
        changed = False
        try:
            entries = parse_page(page)
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

        for entry in entries:
            if not (entry["status"] == "" or entry["status"] == STATUS_PENDING):
                continue
            changed = True
            entry["status"] = STATUS_PENDING
            update_page(page, entries)
            process(entry)
    
        if changed:
            update_page(page, entries)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Monitor for sipr0n map imports')
    parser.add_argument('--page', default="/var/www/archive/data/pages/simapper.txt", help='Page to monitor')
    parser.add_argument('--log', default="/var/www/lib/simapper.txt", help='Log file')
    args = parser.parse_args()

    run(page=args.page)

if __name__ == "__main__":
    main()
