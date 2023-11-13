# TODO: Add docstrings
# TODO: Make catch more similar images
# TODO: Make exit gracefully on full completion

from enum import Enum
from hashlib import sha256
from multiprocessing import cpu_count, Event as MultiprocessingEvent, Lock, Manager, Process, Queue
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event as MultiprocessingEventType, Lock as LockType
from pathlib import Path
from PIL import Image as PILImage, ImageTk
from queue import Empty
from sys import stdout
from threading import Thread
from time import sleep
from tkinter import *  # type: ignore
from tkinter import filedialog, messagebox

from imagehash import average_hash, dhash, phash


def __backup(path: Path) -> None:
	"""Make a backup of the target directory

	Parameters
	----------
	path: Path to the target directory
	"""
	from shutil import copytree
	backup_path = Path(str(path) + "_backup")
	if not backup_path.exists():
		copytree(path, backup_path)


class Main:
	def __init__(self) -> None:
		self.duplicate_queue: Queue[tuple[str, Path, Path, str]] = Queue()
		self.image_map: DictProxy[str, tuple[Path, str]] = Manager().dict()
		self.discovery_complete_flag: MultiprocessingEventType = MultiprocessingEvent()
		self.kill_flag: MultiprocessingEventType = MultiprocessingEvent()
		self.stdout_lock: LockType = Lock()
		self.user_interface = UserInterface(
			self.duplicate_queue,
			self.image_map,
			self.discovery_complete_flag,
			self.kill_flag,
			self.stdout_lock
		)
		root_directory = self.user_interface.build()
		__backup(root_directory)  # TODO: Remove this line
		self.spawn_processes(root_directory)
		self.process_monitor = Thread(target=self.monitor_processes)
		self.process_monitor.start()
		self.user_interface.start()

	def monitor_processes(self) -> None:
		for process in self.processes:
			process.join()
		self.discovery_complete_flag.set()
		print("Discovery complete!")

	def spawn_processes(self, root_directory: Path) -> None:
		directory_queue: Queue[Path] = Queue()
		directory_queue.put(root_directory)
		self.processes: list[Process] = []
		for _ in range(cpu_count() - 2):
			self.processes.append(
				DiscoveryWorker(
					directory_queue,
					self.duplicate_queue,
					self.image_map,
					self.kill_flag,
					self.stdout_lock
				)
			)
		print("Starting processes...")
		for process in self.processes:
			process.start()


class UserInterface:
	class KeepSelection(Enum):
		NEITHER = -1
		BOTH = 0
		LEFT = 1
		RIGHT = 2

	def __init__(
		self,
		duplicate_queue: "Queue[tuple[str, Path, Path, str]]",
		image_map: "DictProxy[str, tuple[Path, str]]",
		discovery_complete_flag: MultiprocessingEventType,
		kill_flag: MultiprocessingEventType,
		stdout_lock: LockType
	) -> None:
		self.duplicate_queue = duplicate_queue
		self.image_map = image_map
		self.discovery_complete_flag = discovery_complete_flag
		self.kill_flag = kill_flag
		self.stdout_lock = stdout_lock
		self.target: tuple[str, Path, Path, str] = ("", Path(), Path(), "")
		self.closed = False

	def build(self) -> Path:
		self.window = Tk()
		self.window.title('Duplicate Image Handler')
		self.window.resizable(width=False, height=False)
		self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

		header = Label(self.window, text="Click image to KEEP")
		self.basic_img = ImageTk.PhotoImage(PILImage.open(r"F:\white.jpg").resize((500, 500), PILImage.ADAPTIVE))
		self.l_button = Button(self.window, command=lambda: self.button_callback(self.KeepSelection.LEFT), height=500, width=500, image=self.basic_img)
		self.l_label = Label(self.window, text="\n")
		self.r_button = Button(self.window, command=lambda: self.button_callback(self.KeepSelection.RIGHT), height=500, width=500, image=self.basic_img)
		self.r_label = Label(self.window, text="\n")
		keep_button = Button(self.window, command=lambda: self.button_callback(self.KeepSelection.BOTH), text="KEEP\nBOTH")
		delete_button = Button(self.window, command=lambda: self.button_callback(self.KeepSelection.NEITHER), text="DELETE\nBOTH")

		header.grid(row=0, column=0, columnspan=11)
		self.l_button.grid(row=1, column=0, columnspan=5, sticky="NW")
		self.l_label.grid(row=2, column=0, columnspan=5, sticky="N")
		self.r_button.grid(row=1, column=6, columnspan=5, sticky="NE")
		self.r_label.grid(row=2, column=6, columnspan=5, sticky="N")
		keep_button.grid(row=1, column=5, sticky="N")
		delete_button.grid(row=2, column=5, sticky="S")

		return Path(filedialog.askdirectory())

	def button_callback(self, selection: KeepSelection) -> None:
		identity_hash, left_image, right_image, right_hash = self.target
		if not identity_hash:
			return
		if selection == self.KeepSelection.NEITHER:
			if not messagebox.askyesno("Delete", "Are you sure you want to delete both images?"):
				return
			self.write_to_stdout(f"Removing {left_image} and {right_image}")
			left_image.unlink()
			right_image.unlink()
			del self.image_map[identity_hash]
		elif selection == self.KeepSelection.LEFT:
			self.write_to_stdout(f"Removing {right_image}")
			right_image.unlink()
		elif selection == self.KeepSelection.RIGHT:
			self.write_to_stdout(f"Removing {left_image}")
			left_image.unlink()
			self.image_map[identity_hash] = (right_image, right_hash)
		self.l_button.configure(image=self.basic_img)
		self.l_label.configure(text="")
		self.r_button.configure(image=self.basic_img)
		self.r_label.configure(text="")
		self.target = ("", Path(), Path(), "")

	def monitor_duplicates(self) -> None:
		while not (
			self.duplicate_queue.empty() and self.discovery_complete_flag.is_set()
		) and not self.kill_flag.is_set():
			try:
				package = self.duplicate_queue.get(True, 1)
				while self.target[0] and not self.kill_flag.is_set():
					sleep(0.2)
				self.stage_duplicates(*package)
			except Empty:
				continue
		while not self.kill_flag.is_set() and self.target[0]:
			sleep(0.2)
		self.write_to_stdout("Exiting...")
		if not self.closed:
			self.on_closing(True)

	def on_closing(self, from_thread: bool = False) -> None:
		self.closed = True
		self.kill_flag.set()
		if not from_thread:
			self.duplicate_monitor.join(2)
		self.window.destroy()

	def stage_duplicates(
		self,
		identity_hash: str,
		left_image: Path,
		right_image: Path,
		right_hash: str
	) -> None:
		self.write_to_stdout(f"Comparing {left_image} and {right_image}")
		if not left_image.exists():
			self.write_to_stdout(f"{left_image} no longer exists!")
			left_image, left_hash = self.image_map.get(identity_hash, (Path(), ""))
			if not left_hash:
				self.image_map[identity_hash] = (right_image, right_hash)
				return
			with right_image.open("rb") as file:
				data = file.read()
			right_hash = sha256(data).hexdigest()
			if left_hash == right_hash:
				with PILImage.open(right_image) as r_img:
					r_width, r_hight = r_img.size
				with PILImage.open(str(left_image.resolve())) as l_img:
					l_width, l_hight = l_img.size
				if l_width * l_hight >= r_width * r_hight:
					self.write_to_stdout(f"Removing {right_image}")
					right_image.unlink()
				else:
					self.write_to_stdout(f"Removing {left_image}")
					self.image_map[identity_hash] = (right_image, right_hash)
					left_image.unlink()
				return
		l_orig = PILImage.open(str(left_image.resolve()))
		r_orig = PILImage.open(str(right_image.resolve()))
		self.l_img = ImageTk.PhotoImage(l_orig.resize((500, 500), PILImage.ADAPTIVE))
		self.r_img = ImageTk.PhotoImage(r_orig.resize((500, 500), PILImage.ADAPTIVE))
		self.l_button.configure(image=self.l_img)
		self.l_label.configure(text=f"{left_image.name}\n{l_orig.height}x{l_orig.width}")
		self.r_button.configure(image=self.r_img)
		self.r_label.configure(text=f"{right_image.name}\n{r_orig.height}x{r_orig.width}")
		self.window.update()
		self.target = (identity_hash, left_image, right_image, right_hash)

	def start(self) -> None:
		self.duplicate_monitor = Thread(target=self.monitor_duplicates)
		self.duplicate_monitor.start()
		self.window.mainloop()

	def write_to_stdout(self, msg: str) -> None:
		with self.stdout_lock:
			print(f"UI: {msg}")
			stdout.flush()


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
				# identity_hash = str(average_hash(image))
				# identity_hash = str(dhash(image))
				identity_hash = str(phash(image))
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


if __name__ == "__main__":
	Main()