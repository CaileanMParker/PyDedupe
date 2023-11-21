from multiprocessing import Event as MultiprocessingEvent, Lock, Process, Queue
from multiprocessing.synchronize import Event as MultiprocessingEventType, Lock as MultiprocessingLockType
from os import walk
from pathlib import Path
from queue import Empty
from sys import argv
from threading import Thread
from time import sleep, time


class SingularDiscovery:
	def __init__(self, base_dir:str, file_lock: MultiprocessingLockType) -> None:
		self.base_dir = base_dir
		self.file_lock = file_lock
		self.file_queue: Queue[Path] = Queue()
		self.kill_flag: MultiprocessingEventType = MultiprocessingEvent()
		Thread(target=self.run).start()

	def discover(self, base_dir: str, file_queue: "Queue[Path]", discovery_complete_flag: MultiprocessingEventType, stdout_lock: MultiprocessingLockType, kill_flag: MultiprocessingEventType) -> None:
		# with stdout_lock:
		# 	print("Starting discovery...")
		for _, _, files in walk(base_dir):
			for file in files:
				file_queue.put(Path(file))
			if kill_flag.is_set():
				break
		# with stdout_lock:
		# 	print("Finished discovery...")
		discovery_complete_flag.set()
		file_queue.close()

	def work(self, file_queue: "Queue[Path]", discovery_complete_flag: MultiprocessingEventType, stdout_lock: MultiprocessingLockType, kill_flag: MultiprocessingEventType) -> None:
		# with stdout_lock:
		# 	print(f"Starting worker...")
		while (not discovery_complete_flag.is_set() or not file_queue.empty()) and not kill_flag.is_set():
			try:
				file = file_queue.get()
				# with stdout_lock:
				# 	print("Working on:", file)
				sleep(0.5)
			except Empty:
				continue
		# with stdout_lock:
		# 	print(f"Stopping worker...")
		file_queue.close()

	def run(self) -> None:
		discovery_complete_flag: MultiprocessingEventType = MultiprocessingEvent()
		stdout_lock: MultiprocessingLockType = Lock()
		# with stdout_lock:
		# 	print("Spawning processes...")
		discovery_process = Process(target=self.discover, args=(self.base_dir, self.file_queue, discovery_complete_flag, stdout_lock, self.kill_flag))
		worker_processes: list[Process] = []
		for _ in range(3):
			worker_processes.append(Process(target=self.work, args=(self.file_queue, discovery_complete_flag, stdout_lock, self.kill_flag)))
		self.start_time = time()
		discovery_process.start()
		for process in worker_processes:
			process.start()
		# with stdout_lock:
		# 	print("Joining processes...")
		for process in worker_processes:
			process.join()
		discovery_process.join()
		self.file_queue.close()
		self.file_queue.join_thread()
		end_time = time()
		print(f"Split time taken: {end_time - self.start_time}")
		with file_lock:
			with open(self.base_dir + "test.txt", "a") as file:
				file.write(f"Split time taken: {end_time - self.start_time}\n")

	def stop(self) -> None:
		self.kill_flag.set()
		while True:
			try:
				if self.file_queue.empty():
					break
				self.file_queue.get(True, 1)
			except Empty:
				break


class SplitDiscovery:
	def __init__(self, base_dir:str, file_lock: MultiprocessingLockType) -> None:
		self.base_dir = base_dir
		self.file_lock = file_lock
		self.directory_queue: Queue[Path] = Queue()
		self.kill_flag: MultiprocessingEventType = MultiprocessingEvent()
		Thread(target=self.run).start()

	def discover_work(self, directory_queue: "Queue[Path]", stdout_lock: MultiprocessingLockType, kill_flag: MultiprocessingEventType) -> None:
		# with stdout_lock:
		# 	print(f"Starting worker...")
		empty_passes = 0
		while not kill_flag.is_set():
			try:
				directory: Path = self.directory_queue.get(True, 1)
				empty_passes = 0
				for child_path in directory.iterdir():
					if kill_flag.is_set():
						break
					if child_path.is_dir():
						# with stdout_lock:
						# 	print("Discovered:", child_path)
						directory_queue.put(child_path)
					elif child_path.is_file():
						# with stdout_lock:
						# 	print("Working on:", child_path)
						sleep(0.5)
			except Empty:
				empty_passes += 1
				if empty_passes >= 10:
					break
			except PermissionError:
				continue
		# with stdout_lock:
		# 	print(f"Stopping worker...")
		directory_queue.close()

	def run(self) -> None:
		self.directory_queue.put(Path(self.base_dir))
		stdout_lock: MultiprocessingLockType = Lock()
		# with stdout_lock:
		# 	print("Spawning processes...")
		worker_processes: list[Process] = []
		for _ in range(4):
			worker_processes.append(Process(target=self.discover_work, args=(self.directory_queue, stdout_lock, self.kill_flag)))
		self.start_time = time()
		for process in worker_processes:
			process.start()
		# with stdout_lock:
		# 	print("Joining processes...")
		for process in worker_processes:
			process.join()
		self.directory_queue.close()
		self.directory_queue.join_thread()
		end_time = time()
		print(f"Single time taken: {end_time - self.start_time}")
		with file_lock:
			with open(self.base_dir + "test.txt", "a") as file:
				file.write(f"Split time taken: {end_time - self.start_time}\n")

	def stop(self) -> None:
		self.kill_flag.set()
		while True:
			try:
				if self.directory_queue.empty():
					break
				self.directory_queue.get(True, 1)
			except Empty:
				break


if __name__ == "__main__":
	base_dir = argv[1]
	if not Path(base_dir).exists():
		raise FileNotFoundError(f"Directory {base_dir} does not exist.")
	file_lock = Lock()
	single = SingularDiscovery(base_dir, file_lock)
	split = SplitDiscovery(base_dir, file_lock)
	input()
	print("Shutting down...")
	single.stop()
	split.stop()