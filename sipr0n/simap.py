import json
import os
import shutil
import datetime


def map_manifest_add_file(basedir, fn, collection, type_, copyright_year=None):
    """
    JSON with explicit copyright information
    """
    assert type_ in ("image", "map")
    jfn = os.path.join(basedir, ".manifest")
    if os.path.exists(jfn):
        j = json.load(open(jfn))
    else:
        j = {
            "files": {},
        }

    if not copyright_year:
        copyright_year = datetime.datetime.now().year

    if fn[0] == "/":
        raise ValueError("Require relative path")
    j["files"][fn] = {
        "collection": collection,
        "type": type_,
        "copyright_year": copyright_year,
    }

    # Be really careful not to corrupt records
    json.dump(j,
              open(jfn + ".tmp", "w"),
              sort_keys=True,
              indent=4,
              separators=(',', ': '))
    if os.path.exists(jfn):
        shutil.move(jfn, jfn + ".old")
    shutil.move(jfn + ".tmp", jfn)
