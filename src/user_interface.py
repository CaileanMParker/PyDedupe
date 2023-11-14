from enum import Enum
from logging import getLogger
from multiprocessing import Queue
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event as MultiprocessingEventType
from pathlib import Path
from PIL import Image as PILImage, ImageTk
from queue import Empty
from threading import Thread
from time import sleep
from tkinter import *  # type: ignore
from tkinter import filedialog, messagebox

from utils import BASE_DIRECTORY


log = getLogger()


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
		kill_flag: MultiprocessingEventType
	) -> None:
		self.blank_image = PILImage.open(BASE_DIRECTORY.joinpath("resources/blank.jpg"))
		self.duplicate_queue = duplicate_queue
		self.image_map = image_map
		self.discovery_complete_flag = discovery_complete_flag
		self.kill_flag = kill_flag
		self.target: tuple[str, Path, Path, str] = ("", Path(), Path(), "")
		self.closed = False

	def build(self) -> Path:
		self.window = Tk()
		self.window.title('Duplicate Image Handler')
		self.window.resizable(width=False, height=False)
		self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

		header = Label(self.window, text="Click image to KEEP")

		self.basic_img = ImageTk.PhotoImage(self.blank_image.resize((500, 500), PILImage.ADAPTIVE))
		self.l_button = Button(
			self.window,
			command=lambda: self.button_callback(self.KeepSelection.LEFT),
			height=500,
			width=500,
			image=self.basic_img
		)
		self.l_label = Label(self.window, text="\n")
		self.r_button = Button(
			self.window,
			command=lambda: self.button_callback(self.KeepSelection.RIGHT),
			height=500,
			width=500,
			image=self.basic_img
		)
		self.r_label = Label(self.window, text="\n")
		keep_button = Button(
			self.window,
			command=lambda: self.button_callback(self.KeepSelection.BOTH),
			text="KEEP\nBOTH"
		)
		delete_button = Button(
			self.window,
			command=lambda: self.button_callback(self.KeepSelection.NEITHER),
			text="DELETE\nBOTH"
		)

		header.grid(row=0, column=0, columnspan=11)
		self.l_button.grid(row=1, column=0, columnspan=5, sticky="NW")
		self.l_label.grid(row=2, column=0, columnspan=5, sticky="N")
		self.r_button.grid(row=1, column=6, columnspan=5, sticky="NE")
		self.r_label.grid(row=2, column=6, columnspan=5, sticky="N")
		keep_button.grid(row=1, column=5, sticky="N")
		delete_button.grid(row=2, column=5, sticky="S")

		log.debug("Waiting for user to select base directory...")
		return Path(filedialog.askdirectory())

	def button_callback(self, selection: KeepSelection) -> None:
		identity_hash, left_image, right_image, right_hash = self.target
		if not identity_hash:
			return
		if selection == self.KeepSelection.NEITHER:
			if not messagebox.askyesno("Delete", "Are you sure you want to delete both images?"):
				return
			log.info("Removing %s and %s", left_image, right_image)
			left_image.unlink()
			right_image.unlink()
			del self.image_map[identity_hash]
		elif selection == self.KeepSelection.LEFT:
			log.info("Removing %s", right_image)
			right_image.unlink()
		elif selection == self.KeepSelection.RIGHT:
			log.info("Removing %s", left_image)
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
		log.debug("Exiting...")
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
		log.debug("Comparing %s and %s", left_image, right_image)
		if not left_image.exists():
			log.debug(f"{left_image} no longer exists!")
			left_image, left_hash = self.image_map.get(identity_hash, (Path(), ""))
			if not left_hash:
				self.image_map[identity_hash] = (right_image, right_hash)
				return
			if left_hash == right_hash:
				with PILImage.open(right_image) as r_img:
					r_width, r_hight = r_img.size
				with PILImage.open(str(left_image.resolve())) as l_img:
					l_width, l_hight = l_img.size
				if l_width * l_hight >= r_width * r_hight:
					log.info("Removing %s", right_image)
					right_image.unlink()
				else:
					log.info("Removing %s", left_image)
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