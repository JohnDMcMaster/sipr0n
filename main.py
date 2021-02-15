import os
from time import sleep
from glob import glob

from PIL import Image
from watchdog.observers import Observer

ALLOWED_ENDINGS = ["png", "jpg", "jpeg"]

PATH = "map/"
THUMBFILELIST = "gallery.txt"

MAX_WIDTH = MAX_HEIGHT = 512

def thumb(path):
	print(path)
	img = Image.open(path)
	img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.ANTIALIAS)
	path, ext = path.rsplit(".", 1)
	img.save(path + ".thumb." + ext)
	

def thumbfilelist():
	thumbpaths = glob("map/**/*.thumb.*", recursive=True)
	with open(THUMBFILELIST, "w+") as f:
		f.write("\n".join(thumbpaths))

class event_handler:
	@staticmethod
	def dispatch(event):
		print(event)
		if event.event_type == "created" and not event.is_directory and ".thumb." not in event.src_path and event.src_path.rsplit(".", 1)[-1].lower() in ALLOWED_ENDINGS:
			thumb(event.src_path)
			thumbfilelist()

observer = Observer()
observer.schedule(event_handler, PATH, recursive=True)
observer.start()

try:
	while True:
		sleep(1)
finally:
	observer.stop()
	observer.join()


