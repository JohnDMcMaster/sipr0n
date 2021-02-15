import os
import argparse
from time import sleep
from glob import glob

import PIL
from PIL import Image
from watchdog.observers import Observer

# Have to disable DecompressionBombError limits because these images are large
PIL.Image.MAX_IMAGE_PIXELS = None

ALLOWED_ENDINGS = ["png", "jpg", "jpeg"]

PATH = "map/"
THUMBFILELIST = "gallery.txt"

MAX_WIDTH = MAX_HEIGHT = 512

def thumb(path):

	if ".thumb." in path:
		return
		
	if path.rsplit(".", 1)[-1].lower() not in ALLOWED_ENDINGS:
		return
		
	if path.split(os.path.sep)[-2] != "single":
		return

	print("Resizing", path)
	img = Image.open(path)
	img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.ANTIALIAS)
	path, ext = path.rsplit(".", 1)
	img.save(path + ".thumb." + ext)
	

def thumbfilelist():
	thumbpaths = glob("map/**/*.thumb.*", recursive=True)
	
	result = []
	
	for path in sorted(thumbpaths, key=lambda path:os.path.getmtime(path), reverse=True):
		tilemappath = None
		parentdir = os.path.dirname(path)
		parentdir_contents = os.listdir(parentdir)
		for siblingdir in parentdir_contents:
			if siblingdir != "single":
				tilemappath = os.path.join(parentdir, siblingdir)
				break
		
		bigpath = path.replace(".thumb", "")
		
		line = path + "\t"
		if tilemappath:
			line += tilemappath
		else:
			line += bigpath
				
		result.append(line)
				
	with open(THUMBFILELIST, "w+") as f:
		f.write("\n".join(result))

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
	observer.schedule(event_handler, PATH, recursive=True)
	observer.start()

	try:
		while True:
			sleep(1)
	finally:
		observer.stop()
		observer.join()

def mode_manual():
	paths = []
	for ending in ALLOWED_ENDINGS:
		paths += glob("map/**/*."+ending, recursive=True)
	
	for path in paths:
		thumb(path)

	thumbfilelist()

if __name__ == "__main__":
	parser = argparse.ArgumentParser("generate image thumbnails and info")
	parser.add_argument("--watch", dest="mode", action="store_const", const=mode_observe, default=mode_manual, help="watch")
	args = parser.parse_args()
	
	args.mode()
