#!/usr/bin/env python3
'''
Take an input directory of image files and output directory sorted into pages
'''

import os
import re
import errno
import subprocess
from sipr0n.util import parse_map_image_vcufe


# https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def index_image_dir(dir_in):
    """Return dict as ret[vendor][chipid][flavor] = file_name"""
    images = []

    for root, dirs, files in os.walk(dir_in):
        for file in files:
            if file.endswith(".jpg"):
                images.append(os.path.join(root, file))

    vendors = {}
    for image in images:
        vendor, chipid, user, flavor, e = parse_map_image_vcufe(image)
        vendorm = vendors.setdefault(vendor, {})
        chipidm = vendorm.setdefault(chipid, {})
        chipidm[flavor] = image

    return vendors


def img2doku(filenames, page_fn, optstr=''):
    subprocess.check_call('img2doku -L %s %s >%s' %
                          (optstr, ' '.join(filenames), page_fn),
                          shell=True)


def run(dir_in, dir_out, img2doku_optstr=''):
    vendors = index_image_dir(dir_in)
    for vendor, chipids in vendors.iteritems():
        vendor_dir = os.path.join(dir_out, vendor)
        mkdir_p(vendor_dir)
        for chipid, filenames in chipids.iteritems():
            page_fn = os.path.join(vendor_dir, "%s.txt" % chipid)
            print("%s" % page_fn)
            for fn in filenames.values():
                print('  %s' % fn)
            img2doku(filenames.values(), page_fn, img2doku_optstr)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate sipr0n wiki template pages from image files')
    parser.add_argument('--verbose',
                        action="store_true",
                        help='Verbose output')
    parser.add_argument('dir_in', help='Input image directory')
    parser.add_argument('dir_out', help='Output page directory')
    args = parser.parse_args()
    run(args.dir_in, args.dir_out)


if __name__ == "__main__":
    main()
