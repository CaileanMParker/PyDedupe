# TODO: Add docstrings
# TODO: Make catch more similar images
# TODO: Make exit gracefully on full completion
# TODO: Make handle other file types
# TODO: Experiment with using a dedicated discovery process and let comparisons happen on a per-image basis
# TODO: Implement logging, not stdout dumps

from multiprocessing import cpu_count, Event as MultiprocessingEvent, Lock, Manager, Process, Queue
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event as MultiprocessingEventType, Lock as LockType
from pathlib import Path
from threading import Thread

from dev_functions import backup
from image_handler import DiscoveryWorker
from user_interface import UserInterface


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
		backup(root_directory)  # TODO: Remove this line
		self.__spawn_processes(root_directory)
		self.process_monitor = Thread(target=self.__monitor_processes)
		self.process_monitor.start()
		self.user_interface.start()

	def __monitor_processes(self) -> None:
		for process in self.processes:
			process.join()
		self.discovery_complete_flag.set()
		print("Discovery complete!")

	def __spawn_processes(self, root_directory: Path) -> None:
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


if __name__ == "__main__":
	Main()