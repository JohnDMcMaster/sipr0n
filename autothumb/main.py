import os
import argparse
from time import sleep
from glob import glob
import shutil

import PIL
from PIL import Image
from watchdog.observers import Observer

# Have to disable DecompressionBombError limits because these images are large
PIL.Image.MAX_IMAGE_PIXELS = None

# 2023-06-23: some large images require this
# Unclear if they are actually damaged, but life moves on with this set
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

GALLERY_IMAGES = 20

ALLOWED_ENDINGS = ["png", "jpg", "jpeg"]

MAP_DIR = "/var/www/map"
if not os.path.exists(MAP_DIR):
    MAP_DIR = "map"
    print("WARNING: dev mode")
assert os.path.exists(MAP_DIR)

THUMBFILELIST = "gallery.txt"

SMALL_MAX_WIDTH = SMALL_MAX_HEIGHT = 300

FORCE_REGEN = False


def thumb(path):

    if ".thumb" in path:
        return

    if path.rsplit(".", 1)[-1].lower() not in ALLOWED_ENDINGS:
        return

    if path.split(os.path.sep)[-2] != "single":
        return

    withoutext, ext = path.rsplit(".", 1)
    smallthumbpath = withoutext + ".thumb." + ext

    if not FORCE_REGEN and os.path.exists(smallthumbpath):
        return

    print("Resizing", path)

    img = Image.open(path)
    img.thumbnail((SMALL_MAX_WIDTH, SMALL_MAX_HEIGHT), Image.ANTIALIAS)
    img.save(smallthumbpath)


def thumbfilelist():
    print("Generating " + THUMBFILELIST)

    thumbpaths = glob(MAP_DIR + "/**/single/*.thumb.*", recursive=True)

    result = []

    for path in sorted(thumbpaths,
                       key=lambda path: os.path.getmtime(path),
                       reverse=True)[:GALLERY_IMAGES]:
        parentdir = os.path.dirname(os.path.dirname(path))

        tilemappath = MAP_DIR + "/" + os.path.sep.join(
            os.path.basename(path).split(".", 1)[0].split("_", 2))

        if not os.path.isdir(tilemappath):
            print("WARNING: tilemap %s doesn't exist for thumb %s" %
                  (tilemappath, path))
            continue

        bigpath = path.replace(".thumb", "")

        def relative(path):
            return path.replace("/var/www/", "")

        line = relative(parentdir) + "\t" + relative(path) + "\t"
        if tilemappath:
            line += relative(tilemappath)
        else:
            line += relative(path)

        result.append(line)

    print("Generated %u thumbnails" % len(result))
    tmp_fn = THUMBFILELIST + ".tmp"
    with open(tmp_fn, "w") as f:
        f.write("\n".join(result))
    print("Shifting tmp into final file")
    shutil.move(tmp_fn, THUMBFILELIST)


class event_handler:
    @staticmethod
    def dispatch(event):
        if event.event_type == "created" and not event.is_directory:
            try:
                thumb(event.src_path)
                thumbfilelist()
            except PIL.UnidentifiedImageError as e:
                print(e)


def mode_observe():
    observer = Observer()
    observer.schedule(event_handler, MAP_DIR, recursive=True)
    observer.start()

    try:
        while True:
            sleep(1)
    finally:
        observer.stop()
        observer.join()


def mode_manual():
    print("Manual mode: scanning")
    paths = []
    for ending in ALLOWED_ENDINGS:
        paths += glob(MAP_DIR + "/**/single/*." + ending, recursive=True)

    print("Manual mode: generating thumbnails from %u files" % len(paths))
    for path in paths:
        thumb(path)

    print("Manual mode: generating gallery.txt")
    thumbfilelist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("generate image thumbnails and info")
    parser.add_argument("--watch",
                        dest="mode",
                        action="store_const",
                        const=mode_observe,
                        default=mode_manual,
                        help="watch")
    parser.add_argument("--force",
                        dest="force",
                        action="store_const",
                        const=True,
                        default=False,
                        help="Force regeneration of existing thumbnails")
    parser.add_argument("--gallery-txt",
                        default="/var/www/gallery.txt",
                        help="Output gallery file name")

    args = parser.parse_args()
    THUMBFILELIST = args.gallery_txt
    FORCE_REGEN = args.force
    args.mode()
