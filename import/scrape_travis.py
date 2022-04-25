#!/usr/bin/env python3

import argparse
from pathlib import Path
import glob
import os


def find_images(dir_in):
    """
    Find high resolution images in directories with .pto
    filter out the snap files and return the resulting remaining .tif

    example:
    $ ls atmel/t44c080c/top10x/ |cat
    snap0001.tif
    snap0002.tif
    snap0003.tif
    snap0004.tif
    snap0005.tif
    snap0006.tif
    snap0007.tif
    snap0008.tif
    snap0009.tif
    snap0010.tif
    snap0011.tif
    snap0012.tif
    snap0013.tif
    snap0014.tif
    top10x.pto
    top10x.tif
    """
    ok = 0
    noks = []
    ret = []
    # scream if two .ptos in the same dir
    found_dirs = set()
    for path in sorted(Path(dir_in).rglob('*.pto')):
        print("")
        print(path)

        dir_path = os.path.dirname(path)
        if dir_path in found_dirs:
            print("duplicate .pto")
            noks.append(str(path))
            continue
        found_dirs.add(dir_path)

        dir_tifs = glob.glob(dir_path + "/*.tif")
        dir_tifs = [
            x for x in dir_tifs if not os.path.basename(x).find("snap") == 0
        ]
        if len(dir_tifs) != 1:
            print("nok :(")
            noks.append(str(path))
            continue
        hi_tif = dir_tifs[0]
        ret.append(hi_tif)
        ok += 1
    print("")
    print("ok: %s" % ok)
    print("nok: %s" % len(noks))
    for fn in sorted(noks):
        print("  %s" % fn)
    return set(ret)


def run(dir_in):
    completed_images = set()
    all_images = find_images(dir_in)


def main():
    parser = argparse.ArgumentParser(description='Import travis archive')
    parser.add_argument('--verbose', '-v', action='store_true', help='verbose')
    parser.add_argument('dir_in',
                        default="/home/mcmaster/buffer/ic/travis/goodchips2",
                        nargs="?",
                        help='File name in')
    args = parser.parse_args()

    run(dir_in=args.dir_in)


if __name__ == "__main__":
    main()
