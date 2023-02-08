#!/usr/bin/env python3

import argparse
from pathlib import Path
import glob
import os
import datetime
import json
from collections import OrderedDict
import requests
from sipr0n import util
import subprocess
import hashlib


def load_completed_db():
    return set()


def load_patches():
    return {
        "dirs": {
            # ti/tms320lc541b/green/green.pto: nok :( (too many images: 0)
            "ti/tms320lc541b/green": {
                "unstitched": True,
            },
            # ti/rf430frl152/layer1/rf430frl152-top.pto: nok :( (too many images: 3)
            # logo.tif, probepoints.tif
            "ti/rf430frl152/layer1": {
                "use_image": "rf430frl152-top_blended_fused.tif",
            },
            # ti/rf430tal152/10x/top10.pto: nok :( (too many images: 2)
            # logo.tif
            "ti/rf430tal152/10x": {
                "use_image": "top10_blended_fused.tif",
            },
            # znation/z32h330/z32h330.pto: nok :( (too many images: 22)
            "znation/z32h330": {
                "use_image": "batch_blended_fused.tif",
            },
        },
        "images": {
            "casio/fx82ms/fx82ms-top_blended_fused.tif": {
                "flavor": "mz",
            }
        }
    }


def find_images(dir_in, patches, verbose=False):
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



    mcmaster@necropolis:~/buffer/ic/travis/goodchips2/nxp/tF1371C/top10x$ ls |cat
    snap0058.tif
    snap0059.tif
    snap0060.tif
    snap0061.tif
    snap0062.tif
    snap0063.tif
    snap0064.tif
    snap0065.tif
    snap0066.tif
    snap0067.tif
    snap0068.tif
    snap0069.tif
    tF1371C_blended_fused.tif
    tF1371C.pto
    tF1371C.tif

    fused one appears to have lighting optimization
    """
    ok = 0
    noks = {}
    ret = []

    def mkrel(fn):
        return fn.replace(dir_in + "/", "")

    def fail(msg):
        noks[mkrel(str(pto_path))] = msg

    # scream if two .ptos in the same dir
    found_dirs = set()
    for pto_path in sorted(Path(dir_in).rglob('*.pto')):
        if 0 and str(
                pto_path
        ) != "/home/mcmaster/buffer/ic/travis/goodchips2/microchip/pic18f452/top5x/top5x.pto":
            continue
        print("")
        print(pto_path)
        dir_path = os.path.dirname(pto_path)

        # Skip known stitch failures
        dir_path_rel = mkrel(dir_path)
        dir_patch = patches["dirs"].get(dir_path_rel)
        if dir_patch and dir_patch.get("unstitched"):
            continue

        if dir_path in found_dirs:
            verbose and fail("duplicate .pto (already processed dir)")
            continue
        found_dirs.add(dir_path)

        if len(glob.glob(dir_path)) != 1:
            fail("duplicate .pto (found original duplicate)")
            continue

        use_image = dir_patch and dir_patch.get("use_image")
        # Override when ambiguous
        if use_image:
            hi_tif = dir_path + "/" + use_image
        else:
            dir_tifs = glob.glob(dir_path + "/*.tif")
            dir_tifs = [
                x for x in dir_tifs
                if not os.path.basename(x).find("snap") == 0
            ]

            # Maybe a blended image?
            # take the blended if possible
            if len(dir_tifs) == 2:
                """
                If one has blended and one doesn't, take it
                ex:
                tF1371C_blended_fused.tif
                tF1371C.tif
                """
                a = dir_tifs[0].replace("_blended_fused.tif", ".tif")
                b = dir_tifs[1].replace("_blended_fused.tif", ".tif")
                # is first fused?
                if dir_tifs[0] == b:
                    del dir_tifs[0]
                # is second fused?
                elif dir_tifs[1] == a:
                    del dir_tifs[1]

            if len(dir_tifs) != 1:
                fail("nok :( (too many images: %u)" % len(dir_tifs))
                print(dir_tifs)
                continue
            hi_tif = dir_tifs[0]

        ret.append(hi_tif)
        ok += 1
    print("")
    print("Finished image find loop")
    print("ok: %s" % ok)
    print("nok: %s" % len(noks))
    for pto_fn, msg in noks.items():
        print("  %s: %s" % (pto_fn, msg))
    return ret, noks


def parse_image(image_path):
    """
    return vendor, product, flavor

    ti/msp430f449/rom50x/rom50x.tif
    wch/ch32v307/top10x/top10x.tif
    microchip/pic16c57/dirty/pic16c57_blended_fused.tif

    seems to be pretty reliable vendor/chipid/flavor
    let see how many conform to this


    Finished name parse loop
    ok: 43
    nok: 4
      nintendo/cicnes6113b1/nescic_blended_fused.tif: failed to parse
      lapis/610q112/10x/top/top.tif: failed to parse
      casio/casio3208/casio3208_blended_fused.tif: failed to parse
      casio/fx82ms/fx82ms-top_blended_fused.tif: failed to parse

    guess flavor

    """
    flagged = False

    image_path = image_path.lower()
    parts = image_path.split("/")
    # common case
    if len(parts) == 4:
        vendor, chipid, flavor, _fn = parts
    # occasionally flavor is omitted
    elif len(parts) == 3:
        vendor, chipid, _fn = parts
        flavor = "unk"
        # eh these seem good enough
        # flagged = True
    # combine the extra dirs together
    else:
        vendor = parts[0]
        chipid = parts[1]
        flavor = "_".join(parts[2:-1])
    """
    Now munge things like flavor to remove stitching terms if possible
    Also standardize top to mz
    This might result in collisions, so will take some care
    """
    def replace_exact(s, src, dst):
        if s == src:
            return dst
        else:
            return s

    vendor = vendor.replace("_", "-")
    chipid = chipid.replace("_", "-")
    flavor = flavor.replace("top-5x", "top5x")
    flavor = flavor.replace("10x_top", "top10x")
    flavor = replace_exact(flavor, "top5x", "mz_5x")
    flavor = replace_exact(flavor, "top10x", "mz_10x")
    flavor = replace_exact(flavor, "romtop50x", "mz_rom_50x")
    flavor = replace_exact(flavor, "toprom50x", "mz_rom_50x")

    if "top" in flavor:
        flagged = True

    return vendor, chipid, flavor, flagged


def parse_images(dir_in, all_images, completed_images):
    def mkrel(fn):
        return fn.replace(dir_in + "/", "")

    ret = OrderedDict()
    ok = 0
    noks = {}

    def fail(msg):
        noks[mkrel(src_image)] = msg

    for src_image in all_images:
        src_image_rel = mkrel(src_image)
        if src_image_rel in completed_images:
            continue

        print("")
        print(src_image_rel)
        parsed = parse_image(src_image_rel)
        if not parsed:
            fail("failed to parse")
            continue
        vendor, chipid, flavor, flagged = parsed
        print("parsed: %s" % src_image_rel)
        print("  vendor: %s" % vendor)
        print("  chipid: %s" % chipid)
        print("  flavor: %s" % flavor)
        print("  flagged: %s" % flagged)
        if flagged:
            fail("flagged for review (%s, %s, %s)" % (vendor, chipid, flavor))
            continue
        ret[src_image_rel] = {
            # relative to git root dir
            "src_image": src_image_rel,
            # dirless image in single idr
            "single_fn": f"{vendor}_{chipid}_{flavor}.jpg",
            "vendor": vendor,
            "chipid": chipid,
            "flavor": flavor,
        }
        ok += 1
    print("")
    print("Finished name parse loop")
    print("ok: %s" % ok)
    print("nok: %s" % len(noks))
    for pto_fn, msg in noks.items():
        print("  %s: %s" % (pto_fn, msg))
    return ret, noks


def is_collision(entry):
    """
    Check if URL is valid or not
    """
    url = f"https://siliconpr0n.org/map/{entry['vendor']}/{entry['chipid']}/{entry['flavor']}/"
    print(f"Checking {url}...")
    try:
        get = requests.get(url)
        if get.status_code == 404:
            return False
        elif get.status_code == 200:
            return True
        else:
            raise Exception(
                f"{url}: is Not reachable, status_code: {get.status_code}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"{url}: is Not reachable \nErr: {e}")


def sig_images(parsed, dir_in):
    """
    Calculate signatures so if git changes later can detect
    """
    for src_image_rel, entry in parsed.items():
        print(f"Calculating {src_image_rel}...")
        src_image = dir_in + "/" + src_image_rel
        s = subprocess.check_output(f"sha1sum {src_image}", shell=True)
        s = s.strip().split()[0]
        s = util.tostr(s)
        entry["sha1sum"] = s


def validate_images(parsed):
    """
    Ensure images conform before uploading
    Should ideally also check for collisions
    """
    ok = 0
    noks = {}
    new_singles = set()
    for src_image, entry in parsed.items():

        def fail(msg):
            print("fail")
            noks[src_image] = msg

        print("")
        print(f"Checking {src_image}...")
        print(f"Checking {entry['single_fn']}...")
        if entry["single_fn"] in new_singles:
            fail("collision")
            continue
        new_singles.add(entry["single_fn"])
        try:
            util.parse_image_name(entry["single_fn"])
        except util.ParseError:
            fail("parse error")
        # these all validated
        if is_collision(entry):
            fail("collision")
            continue
        ok += 1
        print("ok")

    print("")
    print("Finished image find loop")
    print("ok: %s" % ok)
    print("nok: %s" % len(noks))
    for pto_fn, msg in noks.items():
        print("  %s: %s" % (pto_fn, msg))
    return noks


def copy_images(parsed, dir_in, single_dir):
    for src_image, entry in parsed.items():
        print("")
        print(f"Converting {src_image}...")
        src_fn = dir_in + "/" + src_image
        assert os.path.exists(src_fn)
        dst_fn = os.path.join(single_dir, entry["single_fn"])
        cmd = f"convert -quality 90 {src_fn} {dst_fn}"
        print(cmd)
        subprocess.check_call(cmd, shell=True)


def run(dir_in, verbose=False):
    dir_out = "travis"
    if not os.path.exists(dir_out):
        os.mkdir(dir_out)
    # Writing to travis/2022-04-25_18-25-35
    subdir = datetime.datetime.utcnow().isoformat().replace("T", "_").replace(
        ":", "-").split(".")[0]
    this_dir = dir_out + "/" + subdir
    os.mkdir(this_dir)
    _logger = util.make_iolog(this_dir + '/out.log')

    print("Writing to %s" % this_dir)
    single_dir = this_dir + "/single"
    # user to move here once uploaded
    uploaded_dir = this_dir + "/uploaded"
    os.mkdir(single_dir)
    os.mkdir(uploaded_dir)

    completed_images = load_completed_db()
    patches = load_patches()
    all_images, all_images_noks = find_images(dir_in, patches, verbose=verbose)
    print("")
    parsed, parsed_noks = parse_images(dir_in, all_images, completed_images)
    print("")
    sig_images(parsed, dir_in)
    print("")
    validate_noks = validate_images(parsed)

    open(this_dir + "/all_images.json", "w").write(
        json.dumps(all_images,
                   sort_keys=True,
                   indent=4,
                   separators=(',', ': ')))
    open(this_dir + "/all_images_noks.json", "w").write(
        json.dumps(all_images_noks,
                   sort_keys=True,
                   indent=4,
                   separators=(',', ': ')))
    open(this_dir + "/parsed.json", "w").write(
        json.dumps(parsed, sort_keys=True, indent=4, separators=(',', ': ')))
    open(this_dir + "/parsed_noks.json", "w").write(
        json.dumps(parsed_noks,
                   sort_keys=True,
                   indent=4,
                   separators=(',', ': ')))
    open(this_dir + "/validate_noks.json", "w").write(
        json.dumps(validate_noks,
                   sort_keys=True,
                   indent=4,
                   separators=(',', ': ')))

    copy_images(parsed, dir_in, single_dir)

    with open(this_dir + "/done.txt", "w") as f:
        f.write("huzzah!")

    print("")
    print("")
    print("Glob rejected .ptos: %s" % len(all_images_noks))
    for pto_fn, msg in all_images_noks.items():
        print("  %s: %s" % (pto_fn, msg))
    print("")
    print("Parse rejected images: %s" % len(parsed_noks))
    for im_fn, msg in parsed_noks.items():
        print("  %s: %s" % (im_fn, msg))
    print("")
    print("Validate rejected images: %s" % len(validate_noks))
    for im_fn, msg in validate_noks.items():
        print("  %s: %s" % (im_fn, msg))
    print("")
    print("Images ready: %s" % len(parsed))


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
