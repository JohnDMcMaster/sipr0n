#!/usr/bin/env python3

import subprocess
import re
import os
import glob

def header_pack(wiki_page, collect, vendor, print_pack=True, page_fns_base=set()):
    ret = ""
    ret += f"""\
{{{{tag>collection_{collect} vendor_{vendor} type_unknown year_unknown foundry_unknown}}}}

"""

    ret += f"""
====== Package ======

"""

    if print_pack:
        pack_top = True
        pack_btm = True
        if len(page_fns_base):
            pack_top = "pack_top.jpg" in page_fns_base
            pack_btm = "pack_btm.jpg" in page_fns_base
        if pack_top:
            ret += f"""\
{{{{:{wiki_page}:pack_top.jpg?300|}}}}

<code>
</code>
"""
        if pack_btm:
            ret += f"""\
{{{{:{wiki_page}:pack_btm.jpg?300|}}}}

<code>
</code>
"""
    else:
        ret += "Unknown"

    ret += """

====== Die ======

<code>
</code>

"""
    return ret


# Keep pr0nmap/main.py and sipr0n/img2doku.py in sync
def parse_image_name(fn):
    fnbase = os.path.basename(fn)
    m = re.match(r'([a-z0-9\-]+)_([a-z0-9\-]+)_(.*).jpg', fnbase)
    if not m:
        raise Exception("Non-confirming file name (need vendor_chipid_flavor.jpg): %s" % (fn,))
    vendor = m.group(1)
    chipid = m.group(2)
    flavor = m.group(3)
    return (fnbase, vendor, chipid, flavor)

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
    
    _fnbase, vendor, chipid, _flavor = parse_image_name(map_fns[0])
    return map_fns, page_fns, vendor, chipid

def run(fns, print_links=True, collect="mcmaster", nspre="", mappre="map", host="https://siliconpr0n.org",
        print_pack=True, write=False, overwrite=False, write_lazy=False, print_=True):
    map_fns, page_fns, vendor, chipid = process_fns(fns)

    wiki_page = f"{nspre}{collect}:{vendor}:{chipid}"
    wiki_url = f"{host}/archive/doku.php?id={wiki_page}" 
    map_chipid_url = f"{host}/{mappre}/{vendor}/{chipid}"

    if print_links:
        print(wiki_url)
        print(wiki_url + ":s")
        print("")
        print("")

    page_fns_base = set()
    for fn in sorted(page_fns):
        page_fns_base.add(os.path.basename(fn)) 

    out = ""
    out += header_pack(wiki_page=wiki_page, collect=collect, vendor=vendor, print_pack=print_pack, page_fns_base=page_fns_base)

    if page_fns:
        for fn in sorted(page_fns):
            fn = os.path.basename(fn)
            page_fns_base.add(fn) 
            if fn in ("pack_top.jpg", "pack_btm.jpg"):
                continue
            out += f"{{{{:{wiki_page}:{fn}?300|}}}}\n"
            out += "\n"

    for fn in map_fns:
        fnbase, vendor_this, chipid_this, flavor = parse_image_name(fn)
        assert vendor == vendor_this
        assert chipid == chipid_this
        
        # vendor_chpiid_flavor.jpg JPEG 1158x750 1158x750+0+0 8-bit sRGB 313940B 0.000u 0:00.000
        identify = subprocess.check_output(f"identify {fn}", shell=True, text=True)
        wh = identify.split(" ")[2]
        size = identify.split(" ")[6]
        out += f"""\
[[{map_chipid_url}/{flavor}/|{flavor}]]

  * [[{map_chipid_url}/single/{fnbase}|Single]] ({wh}, {size})

"""
    def try_write():
        wiki_data_dir = "/var/www/wiki/data"
        page_path = wiki_data_dir + "/pages/" + wiki_page.replace(":", "/") + ".txt"

        if os.path.exists(page_path):
            if write_lazy:
                print("Skip write (lazy: already exists)")
                return False
            if not overwrite:
                raise Exception(f"Refusing to overwrite existing page {page_path}")
        # Might be the first page for this vendor (or maybe even user?)
        vendor_dir = os.path.dirname(page_path)
        # There should at least be a user landing page
        # Leave this off for now
        # user_dir = os.path.dirname(vendor_dir)
        # if not os.path.exists(user_dir):
        #    os.mkdir(user_dir)
        if not os.path.exists(vendor_dir):
            write_lazy and print("Making vendor dir " + vendor_dir)
            os.mkdir(vendor_dir)
        open(page_path, "w").write(out)
        write_lazy and print("Wrote to " + page_path)
        # subprocess.run(f"sudo chown www-data:www-data {page_path}", shell=True)
        return True
    wrote = False
    if print_:
        print(out)
    if write:
        wrote = try_write()
    return (out, wiki_page, wiki_url, map_chipid_url, wrote)

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

    parser = argparse.ArgumentParser(description='Generate a sipr0n wiki page from image files from the same page')
    parser.add_argument('--verbose', action="store_true", help='Verbose output')
    parser.add_argument('--write', action="store_true", help='Directly write page into dokuwiki database')
    parser.add_argument('--overwrite', action="store_true", help='Overwrite exist page')
    parser.add_argument('--collect', default="mcmaster", help="")
    parser.add_argument('--nspre', default="", help="wiki namespace prefix")
    parser.add_argument('--mappre', default="map", help="map url prefix")
    add_bool_arg(parser, '--pack', default=True, help='add package image')
    add_bool_arg(parser, '--link', default=True, help='no link text')
    parser.add_argument('fns_in', nargs="+")
    args = parser.parse_args()
    run(fns=args.fns_in, print_pack=args.pack, collect=args.collect, write=args.write, overwrite=args.overwrite, nspre=args.nspre, mappre=args.mappre)

if __name__ == "__main__":
    main()
