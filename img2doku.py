#!/usr/bin/env python3

from sipr0n.util import parse_map_image_vcufe

import subprocess
import os
import glob


def commented_image(wiki_page, fn, width=300):
    assert os.path.basename(fn) == fn
    return f"""\

{{{{:{wiki_page}:{fn}?{width}|}}}}

<code>
</code>
"""


def simple_image(wiki_page, fn, width=300):
    assert os.path.basename(fn) == fn
    return f"""\
{{{{:{wiki_page}:{fn}?{width}|}}}}
"""


def header_pack(wiki_page,
                collect,
                vendor,
                print_pack=True,
                page_fns_base=set(),
                code_txt=None,
                header_txt=None,
                force_tags=None,
                force_fns=None):
    ret = ""
    # {{tag>collection_mcmaster vendor_atmel type_ccd year_unknown foundry_unknown tech_unknown}}
    if force_tags is not None:
        ret += "{{tag>" + " ".join(force_tags) + "}}\n"
    else:
        ret += f"""\
{{{{tag>collection_{collect} vendor_{vendor} type_unknown year_unknown foundry_unknown}}}}
"""
    ret += "\n"

    if header_txt:
        ret += header_txt + "\n"

    if code_txt:
        ret += "<code>\n"
        ret += code_txt + "\n"
        ret += "</code>\n"

    if force_fns is not None:
        for fn in force_fns.get("header", []):
            ret += simple_image(wiki_page, fn)
            ret += "\n"

    ret += f"""
====== Package ======
"""

    if force_fns is not None:
        for fn in force_fns.get("package", []):
            ret += commented_image(wiki_page, fn)
        if len(force_fns.get("package", [])) == 0:
            ret += "\nUnknown\n"
    else:
        if print_pack:
            pack_top = True
            pack_btm = True
            assert page_fns_base is not None
            if len(page_fns_base):
                pack_top = "pack_top.jpg" in page_fns_base
                pack_btm = "pack_btm.jpg" in page_fns_base
            if pack_top:
                ret += commented_image(wiki_page, "pack_top.jpg")
            if pack_btm:
                ret += commented_image(wiki_page, "pack_btm.jpg")
        else:
            ret += "Unknown\n"

    ret += "\n"
    ret += """
====== Die ======

"""
    return ret


def process_fns(fns):
    """
    Support two inputs:
    -A single input that is a directory containing:
        Misc files, which will be added to the page
        A directory called "single" which contains map files
    -Individual .jpg files which are for map
    
    Since vendor and chipid are from map file name, at least one is required currently
    """
    map_fns = []
    page_fns = []

    for fn in fns:
        if os.path.isdir(fn):
            page_fns += list(glob.glob(fn + "/*.jpg"))
            map_fns += list(glob.glob(fn + "/single/*.jpg"))
        else:
            map_fns.append(fn)

    vendor, chipid, _user, _flavor, _ext = parse_map_image_vcufe(map_fns[0])
    return map_fns, page_fns, vendor, chipid


def image_2_thumb_name(fn):
    vendor_this, chipid_this, user_this, flavor, ext = parse_map_image_vcufe(
        fn)
    return f"{vendor_this}_{chipid_this}_{user_this}_{flavor}.thumb.{ext}"


def add_maps(map_fns, vendor, chipid, user, map_chipid_url):
    out = ""
    for fn in map_fns:
        fnbase = os.path.basename(fn)
        vendor_this, chipid_this, user_this, flavor, _ext = parse_map_image_vcufe(
            fn)
        assert vendor == vendor_this
        assert chipid == chipid_this
        assert user == user_this

        # vendor_chpiid_flavor.jpg JPEG 1158x750 1158x750+0+0 8-bit sRGB 313940B 0.000u 0:00.000
        identify = subprocess.check_output(["identify", fn],
                                           text=True)
        wh = identify.split(" ")[2]
        size = identify.split(" ")[6]
        thumb_name = image_2_thumb_name(fnbase)
        image_thumb_txt = "{{" + f"{map_chipid_url}/single/{thumb_name}" + "}}"
        out += f"""\
{image_thumb_txt}

[[{map_chipid_url}/{user}_{flavor}/|{flavor}]]

  * [[{map_chipid_url}/single/{fnbase}|Single]] ({wh}, {size})
"""
    return out


def run(
    hi_fns=[],
    print_links=True,
    collect=None,
    nspre="",
    mappre="map",
    host="https://siliconpr0n.org",
    print_pack=True,
    write=False,
    overwrite=False,
    write_lazy=False,
    print_=True,
    www_dir="/var/www",
    code_txt=None,
    header_txt=None,
    # Auto guess if given hi_fn
    vendor=None,
    chipid=None,
    page_fns=[],
    map_fns=[],
    force_tags=None,
    force_fns=None):
    """
    hi_fns: to turn into /map entries under "die"
    print_links: debug output
    nspre: namespace prefix for protected namespace
    
    page_fns: untagged files. Will try to guess what they are for
    force_header_fns: if given add these images to the heaer
    force_pack_fns: if given add these images to the pack section and don't try to guess
    force_die_fns: if given add these images to the die section and don't try to guess
    """

    if len(hi_fns):
        map_fns, page_fns, vendor, chipid = process_fns(hi_fns)
    else:
        assert vendor
        assert chipid

    wiki_page = f"{nspre}{collect}:{vendor}:{chipid}"
    wiki_url = f"{host}/archive/doku.php?id={wiki_page}"
    map_chipid_url = f"{host}/{mappre}/{vendor}/{chipid}"

    wiki_data_dir = www_dir + "/archive/data"
    page_path = wiki_data_dir + "/pages/" + wiki_page.replace(":",
                                                              "/") + ".txt"

    exists = os.path.exists(page_path)

    if print_links:
        print(wiki_url)
        print(wiki_url + ":s")
        print("")
        print("")

    if page_fns is not None:
        page_fns_base = set()
        for fn in sorted(page_fns):
            page_fns_base.add(os.path.basename(fn))
    else:
        page_fns_base = None

    out = ""
    if not exists:
        out += header_pack(wiki_page=wiki_page,
                           collect=collect,
                           vendor=vendor,
                           print_pack=print_pack,
                           page_fns_base=page_fns_base,
                           code_txt=code_txt,
                           header_txt=header_txt,
                           force_tags=force_tags,
                           force_fns=force_fns)

        if page_fns:
            for fn in sorted(page_fns):
                fn = os.path.basename(fn)
                page_fns_base.add(fn)
                if fn in ("pack_top.jpg", "pack_btm.jpg"):
                    continue
                out += f"{{{{:{wiki_page}:{fn}?300|}}}}\n"
                out += "\n"

        if force_fns is not None:
            for fn in force_fns.get("die", []):
                out += simple_image(wiki_page, fn)
                out += "\n"

        out += "<code>\n"
        out += "</code>\n"
        out += "\n"

    out += add_maps(map_fns,
                    vendor=vendor,
                    chipid=chipid,
                    user=collect,
                    map_chipid_url=map_chipid_url)

    if exists and force_fns:
        # Instead of placing images in specific places
        # just place them all at the end
        new_fns = []
        for image_set in force_fns.values():
            new_fns += image_set
        for fn in sorted(new_fns):
            out += simple_image(wiki_page, fn)
            out += "\n"

    def try_write():
        if exists and not write_lazy and not overwrite:
            raise Exception(f"Refusing to overwrite existing page {page_path}")
        # Might be the first page for this vendor (or maybe even user?)
        vendor_dir = os.path.dirname(page_path)
        # There should at least be a user landing page
        # Leave this off for now
        user_dir = os.path.dirname(vendor_dir)
        if not os.path.exists(user_dir):
            write_lazy and print("mkdir " + user_dir)
            os.mkdir(user_dir)
        if not os.path.exists(vendor_dir):
            write_lazy and print("mkdir " + vendor_dir)
            os.mkdir(vendor_dir)
        with open(page_path, "a") as f:
            f.write(out)
        write_lazy and print("Wrote to " + page_path)
        # subprocess.run(["sudo", "chown", "www-data:www-data", page_path])
        return True

    wrote = False
    if print_:
        print(out)
    if write:
        wrote = try_write()
    return (out, wiki_page, wiki_url, map_chipid_url, wrote, exists)


def add_bool_arg(parser, yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg,
                        dest=dest,
                        action='store_true',
                        default=default,
                        **kwargs)
    parser.add_argument('--no-' + dashed,
                        dest=dest,
                        action='store_false',
                        **kwargs)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description=
        'Generate a sipr0n wiki page from image files from the same page')
    parser.add_argument('--verbose',
                        action="store_true",
                        help='Verbose output')
    parser.add_argument('--write',
                        action="store_true",
                        help='Directly write page into dokuwiki database')
    parser.add_argument('--overwrite',
                        action="store_true",
                        help='Overwrite exist page')
    parser.add_argument('--collect', default="mcmaster", help="")
    parser.add_argument('--nspre', default="", help="wiki namespace prefix")
    parser.add_argument('--mappre', default="map", help="map url prefix")
    add_bool_arg(parser, '--pack', default=True, help='add package image')
    add_bool_arg(parser, '--link', default=True, help='no link text')
    parser.add_argument('fns_in', nargs="+")
    args = parser.parse_args()
    run(hi_fns=args.fns_in,
        print_pack=args.pack,
        collect=args.collect,
        write=args.write,
        overwrite=args.overwrite,
        nspre=args.nspre,
        mappre=args.mappre)


if __name__ == "__main__":
    main()
