import os
from time import sleep
from glob import glob

from PIL import Image
from watchdog.observers import Observer

# TODO DecompressionBombWarning

ALLOWED_ENDINGS = ["png", "jpg", "jpeg"]

PATH = "map/"
THUMBFILELIST = "gallery.txt"

MAX_WIDTH = MAX_HEIGHT = 512

def thumb(path):
	print("Resizing", path)
	img = Image.open(path)
	img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.ANTIALIAS)
	path, ext = path.rsplit(".", 1)
	img.save(path + ".thumb." + ext)
	

def thumbfilelist():
	thumbpaths = glob("map/**/*.thumb.*", recursive=True)
	
	result = []
	
	for path in thumbpaths:
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
		if event.event_type == "created" and not event.is_directory and ".thumb." not in event.src_path and event.src_path.rsplit(".", 1)[-1].lower() in ALLOWED_ENDINGS and event.src_path.split(os.path.sep)[-2] == "single":
			try:
				thumb(event.src_path)
				thumbfilelist()
			except PIL.UnidentifiedImageError as e:
				print(e)

observer = Observer()
observer.schedule(event_handler, PATH, recursive=True)
observer.start()

try:
	while True:
		sleep(1)
finally:
	observer.stop()
	observer.join()


