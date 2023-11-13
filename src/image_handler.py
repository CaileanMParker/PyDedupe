from hashlib import sha256
from multiprocessing import Process, Queue
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event as MultiprocessingEventType, Lock as LockType
from pathlib import Path
from PIL import Image as PILImage
from queue import Empty
from sys import stdout

from imagehash import average_hash, dhash, phash


class DiscoveryWorker(Process):
	IMAGE_EXTENSIONS = ("JPEG", "JPG", "PNG", "GIF", "TIFF", "RAW", "BMP", "WEBP", "SVG")

	def __init__(
		self,
		directory_queue: "Queue[Path]",
		duplicate_queue: "Queue[tuple[str, Path, Path, str]]",
		image_map: "DictProxy[str, tuple[Path, str]]",
		kill_flag: MultiprocessingEventType,
		stdout_lock: LockType
	) -> None:
		Process.__init__(self)
		self.directory_queue = directory_queue
		self.duplicate_queue = duplicate_queue
		self.image_map = image_map
		self.kill_flag = kill_flag
		self.stdout_lock = stdout_lock

	def check_image(self, image_path: Path) -> None:
		try:
			with PILImage.open(image_path) as image:
				r_width, r_hight = image.size
				identity_hash = str(average_hash(image))
				# identity_hash = str(dhash(image))
				# identity_hash = str(phash(image))
		except:
			return
		with image_path.open("rb") as file:
			data = file.read()
		image_hash = sha256(data).hexdigest()
		mapped_path, mapped_hash = self.image_map.get(identity_hash, (Path(), ""))
		if not mapped_hash:
			self.image_map[identity_hash] = (image_path, image_hash)
			return
		if mapped_hash != image_hash:
			self.write_to_stdout(f"Adding to queue: {image_path}")
			self.duplicate_queue.put((identity_hash, mapped_path, image_path, image_hash))
			return
		with PILImage.open(str(mapped_path.resolve())) as l_img:
			l_width, l_hight = l_img.size
		if l_width * l_hight >= r_width * r_hight:
			self.write_to_stdout(f"Removing {image_path}")
			image_path.unlink()
		else:
			self.write_to_stdout(f"Removing {mapped_path}")
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
		self.write_to_stdout("Starting...")
		empty_passes = 0
		while not self.kill_flag.is_set():
			try:
				directory: Path = self.directory_queue.get(True, 1)
				empty_passes = 0
				self.write_to_stdout(f"Acquired {directory}")
				self.process_directories(directory)
			except Empty:
				empty_passes += 1
				if empty_passes >= 10:
					break
		self.write_to_stdout("Exiting...")

	def write_to_stdout(self, msg: str) -> None:
		with self.stdout_lock:
			print(f"{self.pid}: {msg}")
			stdout.flush()