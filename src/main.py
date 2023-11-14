# TODO: Add docstrings
# TODO: Make catch more similar images
# TODO: Make exit gracefully on full completion
# TODO: Make handle other file types
# TODO: Experiment with using a dedicated discovery process and let comparisons happen on a per-image basis

from logging import DEBUG, Formatter, getLevelName, getLogger, handlers, WARNING
from multiprocessing import cpu_count, Event as MultiprocessingEvent, Manager, Process, Queue
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event as MultiprocessingEventType
from pathlib import Path
from threading import Thread

from image_handler import DiscoveryWorker
from user_interface import UserInterface
from utils import backup, BASE_DIRECTORY, CONFIGS


LOG_PATH = Path(CONFIGS["logging"]["path"])
if not LOG_PATH.is_absolute():
	LOG_PATH = BASE_DIRECTORY.joinpath(LOG_PATH)
if not LOG_PATH.parent.exists():
	LOG_PATH = BASE_DIRECTORY.joinpath("logs", LOG_PATH.name)
LOG_LEVEL = getLevelName(CONFIGS["logging"]["level"])

log = getLogger()
log.setLevel(LOG_LEVEL)
file_handler = handlers.RotatingFileHandler(LOG_PATH, maxBytes=99999999, backupCount=2)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(file_handler)
getLogger("PIL").setLevel(WARNING)

class Main:
	def __init__(self) -> None:
		log.info("Starting application...")
		self.duplicate_queue: Queue[tuple[str, Path, Path, str]] = Queue()
		self.image_map: DictProxy[str, tuple[Path, str]] = Manager().dict()
		self.discovery_complete_flag: MultiprocessingEventType = MultiprocessingEvent()
		self.kill_flag: MultiprocessingEventType = MultiprocessingEvent()
		self.user_interface = UserInterface(
			self.duplicate_queue,
			self.image_map,
			self.discovery_complete_flag,
			self.kill_flag
		)
		root_directory = self.user_interface.build()
		log.debug("User selected base directory: %s", root_directory)
		if LOG_LEVEL == DEBUG:
			backup(root_directory)
		self.__spawn_processes(root_directory)
		self.process_monitor = Thread(target=self.__monitor_processes)
		self.process_monitor.start()
		self.user_interface.start()

	def __monitor_processes(self) -> None:
		for process in self.processes:
			process.join()
		self.discovery_complete_flag.set()
		log.debug("Discovery complete!")

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
					self.kill_flag
				)
			)
		log.debug("Spawning processes...")
		for process in self.processes:
			process.start()


if __name__ == "__main__":
	Main()