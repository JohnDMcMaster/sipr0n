from sipr0n import env
"""
Think this format should be shuffle agnostic
NOTE: there may be collisions for a (vendor, chipid, basename)
We'll have to see how easy they are to resolve / how many

{
    "altera": {
        "ep900": [
            {
                "type": "map",
                "collection": "mcmaster",
                "vendor": "altera",
                "chipid": "ep900",
                "basename": "mz_mit20x",
            }
            {
                "type": "image",
                "collection": "mcmaster",
                "vendor": "altera",
                "chipid": "ep900",
                "dirname": "single",
                "basename": "mz_mit20x.jpg",
            }
        ],
    }
}
"""

class CollectionNotFound(Exception):
    pass


def add_meta_image(meta, vendor, chipid, collection, dirname, basename):
    assert vendor
    assert chipid
    assert collection
    assert basename
    assert dirname
    j = {
        "type": "image",
        "collection": collection,
        "vendor": vendor,
        "chipid": chipid,
        "dirname": dirname,
        "basename": basename,
    }

    vendorj = meta.setdefault(vendor, {})
    chipidj = vendorj.setdefault(chipid, [])
    chipidj.append(j)
    print(f"    image from {collection}: {vendor} {chipid} {basename}")
    return j


def add_meta_map(meta, vendor, chipid, collection, basename):
    assert vendor
    assert chipid
    # assert collection
    assert basename
    j = {
        "type": "map",
        "vendor": vendor,
        "chipid": chipid,
        "basename": basename,
    }
    if collection:
        j["collection"] = collection

    vendorj = meta.setdefault(vendor, {})
    chipidj = vendorj.setdefault(chipid, [])
    chipidj.append(j)
    print(f"    map from {collection}: {vendor} {chipid} {basename}")
    return j


def load_copyright_db():
    """
    dict of
    collection : copyright
    """
    env.setup_env_default()
    ret = {}
    print("Loading", env.COPYRIGHT_TXT)
    f = open(env.COPYRIGHT_TXT, "r")
    try:
        f.readline()
        for l in f:
            l = l.strip()
            if not l:
                continue
            _prefix, collection, copyright, _notes, _postfix = l.split("|")
            ret[collection.strip()] = copyright.strip()
        return ret
    finally:
        f.close()


def default_copyright(collection):
    """
    cat /var/www/archive/data/pages/copyright.txt
    ^ User ^ Copyright ^ Note ^
    | mcmaster | John McMaster, CC-BY |  |
    """
    f = open(env.COPYRIGHT_TXT, "r")
    try:
        f.readline()
        for l in f:
            l = l.strip()
            if not l:
                continue
            _prefix, this_collection, copyright, _notes, _postfix = l.split(
                "|")
            this_collection = this_collection.strip()
            copyright = copyright.strip()
            if collection == this_collection:
                return copyright
        else:
            raise CollectionNotFound("Failed to find copyright for " + collection)
    finally:
        f.close()

def assert_collection_exists(collection):
    # throws an exception as a side effect
    default_copyright(collection)
