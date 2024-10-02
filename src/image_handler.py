from hashlib import sha256
from logging import getLogger
from multiprocessing import Process, Queue
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event as MultiprocessingEventType
from pathlib import Path
from PIL import Image as PILImage
from queue import Empty

from imagehash import average_hash, dhash, phash


log = getLogger()


class DiscoveryWorker(Process):
	IMAGE_EXTENSIONS = ("JPEG", "JPG", "PNG", "GIF", "TIFF", "RAW", "BMP", "WEBP", "SVG")

	def __init__(
		self,
		directory_queue: "Queue[Path]",
		duplicate_queue: "Queue[tuple[str, Path, Path, str]]",
		image_map: "DictProxy[str, tuple[Path, str]]",
		kill_flag: MultiprocessingEventType
	) -> None:
		Process.__init__(self)
		self.directory_queue = directory_queue
		self.duplicate_queue = duplicate_queue
		self.image_map = image_map
		self.kill_flag = kill_flag

	def check_image(self, image_path: Path) -> None:
		try:
			with PILImage.open(image_path) as image:
				r_width, r_hight = image.size
				identity_hash = str(average_hash(image))  # comparative hash used to judge similarity to other images
				# identity_hash = str(dhash(image))
				# identity_hash = str(phash(image))
		except:
			return
		with image_path.open("rb") as file:
			data = file.read()
		image_hash = sha256(data).hexdigest()  # strict hash used to identify equivalent images
		mapped_path, mapped_hash = self.image_map.get(identity_hash, (Path(), ""))
		if not mapped_hash:
			self.image_map[identity_hash] = (image_path, image_hash)
			return
		if mapped_hash != image_hash:
			log.debug("(%s) Adding to queue: %s", self.pid, image_path)
			self.duplicate_queue.put((identity_hash, mapped_path, image_path, image_hash))
			return
		with PILImage.open(str(mapped_path.resolve())) as l_img:
			l_width, l_hight = l_img.size
		if l_width * l_hight >= r_width * r_hight:
			log.info("(%s) Removing %s", self.pid, image_path)
			image_path.unlink()
		else:
			log.info("(%s) Removing %s", self.pid, mapped_path)
			self.image_map[identity_hash] = (image_path, image_hash)
			mapped_path.unlink()

	def process_directories(self, directory: Path) -> None:
		for child_path in directory.iterdir():
			if self.kill_flag.is_set():
				return
			if child_path.is_dir():
				self.directory_queue.put(child_path)
			elif child_path.is_file() and child_path.suffix[1:].upper() in self.IMAGE_EXTENSIONS:
				self.check_image(child_path)

	def run(self) -> None:
		log.debug("(%s) Starting...", self.pid)
		empty_passes = 0
		while not self.kill_flag.is_set():
			try:
				directory: Path = self.directory_queue.get(True, 1)
				empty_passes = 0
				log.debug("(%s) Acquired %s", self.pid, directory)
				self.process_directories(directory)
			except Empty:
				empty_passes += 1
				if empty_passes >= 10:
					break
		log.debug("(%s) Exiting...", self.pid)