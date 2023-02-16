import json
import os
import shutil


def map_manifest_add_file(basedir, fn, collection, type_):
    """
    JSON with explicit copyright information
    """
    assert type_ in ("image", "map")
    jfn = os.path.join(basedir, ".manfiest")
    if os.path.exists(jfn):
        j = json.load(open(jfn))
    else:
        j = {
            "files": {},
        }

    if fn[0] == "/":
        raise ValueError("Require relative path")
    j["files"][fn] = {
        "collection": collection,
        "type": type_,
    }

    # Be really careful not to corrupt records
    json.dump(j,
              open(jfn + ".tmp", "w"),
              sort_keys=True,
              indent=4,
              separators=(',', ': '))
    shutil.move(jfn, jfn + ".old")
    shutil.move(jfn + ".tmp", jfn)
