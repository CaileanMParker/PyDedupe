#attempt with multiprocessing pool

from ctypes import c_byte
from multiprocessing import Event as MultiprocessingEvent, Lock, Pool, Process, Queue, Value
from multiprocessing.synchronize import Event as MpEventT, Lock as MpLockT
from multiprocessing.sharedctypes import Synchronized as MpSynchronizedT
from os import walk
from pathlib import Path
from queue import Empty
from sys import argv
from threading import Thread
from time import sleep, time


class SingularDiscovery:
	def __init__(self, base_dir:str, file_lock: MpLockT, delay: float) -> None:
		self.base_dir = base_dir
		self.file_lock = file_lock
		self.delay = delay
		self.file_queue: Queue[Path] = Queue()
		self.kill_flag: MpEventT = MultiprocessingEvent()
		Thread(target=self.run).start()

	def discover(self, base_dir: str, file_queue: "Queue[Path]", discovery_complete_flag: MpEventT, stdout_lock: MpLockT, kill_flag: MpEventT) -> None:
		# with stdout_lock:
		# 	print("Starting discovery...")
		for _, _, files in walk(base_dir):
			for file in files:
				file_queue.put(Path(file))
			if kill_flag.is_set():
				break
		# with stdout_lock:
		# 	print(f"Finished discovery...")
		discovery_complete_flag.set()
		file_queue.close()

	def work(self, file_queue: "Queue[Path]", discovery_complete_flag: MpEventT, stdout_lock: MpLockT, kill_flag: MpEventT, delay: float) -> None:
		# with stdout_lock:
		# 	print("Starting worker...")
		while (not discovery_complete_flag.is_set() or not file_queue.empty()) and not kill_flag.is_set():
			try:
				file = file_queue.get(True, 1)
				# with stdout_lock:
				# 	print("Working on:", file)
				sleep(delay)
			except Empty:
				continue
		# with stdout_lock:
		# 	print("Stopping worker...")
		file_queue.close()

	def run(self) -> None:
		discovery_complete_flag: MpEventT = MultiprocessingEvent()
		stdout_lock: MpLockT = Lock()
		# with stdout_lock:
		# 	print("Spawning processes...")
		discovery_process = Process(target=self.discover, args=(self.base_dir, self.file_queue, discovery_complete_flag, stdout_lock, self.kill_flag))
		worker_processes: list[Process] = []
		for _ in range(3):
			worker_processes.append(Process(target=self.work, args=(self.file_queue, discovery_complete_flag, stdout_lock, self.kill_flag, self.delay)))
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
		print(f"Single time taken: {end_time - self.start_time}")
		# with file_lock:
		# 	with open(self.base_dir + "\\test.txt", "a") as file:
		# 		file.write(f"Single time taken: {end_time - self.start_time} Delay: {self.delay}\n")

	def stop(self) -> None:
		self.kill_flag.set()
		while True:
			try:
				if self.file_queue.empty():
					break
				self.file_queue.get(True, 1)
			except (Empty, OSError):
				break


class SplitDiscovery:
	def __init__(self, base_dir:str, file_lock: MpLockT, delay: float) -> None:
		self.base_dir = base_dir
		self.file_lock = file_lock
		self.delay = delay
		self.directory_queue: Queue[Path] = Queue()
		self.kill_flag: MpEventT = MultiprocessingEvent()
		Thread(target=self.run).start()

	def discover_work(self, directory_queue: "Queue[Path]", stdout_lock: MpLockT, kill_flag: MpEventT, delay: float, processes_running: MpSynchronizedT) -> None:
		# with stdout_lock:
		# 	print("Starting worker...")
		while not kill_flag.is_set():
			try:
				directory: Path = self.directory_queue.get(True, 1)
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
						sleep(delay)
			except Empty:
				with processes_running.get_lock():
					processes_running.value -= 1
				while self.directory_queue.empty() and processes_running.value > 0:
					sleep(0.1)
				if processes_running.value == 0:
					break
				with processes_running.get_lock():
					processes_running.value += 1
			except PermissionError:
				continue
		# with stdout_lock:
		# 	print("Stopping worker...")
		directory_queue.close()

	def run(self) -> None:
		self.directory_queue.put(Path(self.base_dir))
		stdout_lock: MpLockT = Lock()
		processes_running: MpSynchronizedT = Value(c_byte, 0)
		# with stdout_lock:
		# 	print("Spawning processes...")
		worker_processes: list[Process] = []
		for _ in range(4):
			processes_running.value += 1
			worker_processes.append(Process(target=self.discover_work, args=(self.directory_queue, stdout_lock, self.kill_flag, self.delay, processes_running)))
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
		print(f"Split time taken: {end_time - self.start_time}")
		self.kill_flag.set()
		# with file_lock:
		# 	with open(self.base_dir + "\\test.txt", "a") as file:
		# 		file.write(f"Split time taken: {end_time - self.start_time} Delay: {self.delay}\n")

	def stop(self) -> None:
		self.kill_flag.set()
		while True:
			try:
				if self.directory_queue.empty():
					break
				self.directory_queue.get(True, 1)
			except (Empty, OSError):
				break


class PoolDiscovery:
	def __init__(self, base_dir: str, file_lock: MpLockT, delay: float) -> None:
		self.base_dir = base_dir
		self.file_lock = file_lock
		self.delay = delay
		self.kill_flag: MpEventT = MultiprocessingEvent()
		Thread(target=self.run).start()

	def discover(self, base_dir: str, stdout_lock: MpLockT, kill_flag: MpEventT) -> None:
		# with stdout_lock:
		# 	print("Starting discovery...")
		with Pool(4, initializer = work_init, initargs = (stdout_lock, self.delay)) as pool:
			for _, _, files in walk(base_dir):
				pool.map_async(work, files, chunksize = (len(files) // 4) + 1)  # type: ignore
				if kill_flag.is_set():
					break
			pool.close()
			pool.join()
		# with stdout_lock:
		# 	print("Finished discovery...")

	def run(self) -> None:
		stdout_lock: MpLockT = Lock()
		# with stdout_lock:
		# 	print("Spawning processes...")
		discovery_process = Process(target=self.discover, args=(self.base_dir, stdout_lock, self.kill_flag))
		self.start_time = time()
		discovery_process.start()
		# with stdout_lock:
		# 	print("Joining processes...")
		discovery_process.join()
		end_time = time()
		print(f"Pool time taken: {end_time - self.start_time}")
		# with file_lock:
		# 	with open(self.base_dir + "\\test.txt", "a") as file:
		# 		file.write(f"Pool time taken: {end_time - self.start_time} Delay: {self.delay}\n")

	def stop(self) -> None:
		self.kill_flag.set()


def work_init(stdout_lock_i: MpLockT, delay_i: float) -> None:
	global stdout_lock, delay
	stdout_lock = stdout_lock_i
	delay = delay_i


def work(file: str) -> None:
	global stdout_lock, delay
	# with stdout_lock:
	# 	print("Working on:", file, flush = True)
	sleep(delay)


if __name__ == "__main__":
	base_dir = argv[1]
	if not Path(base_dir).exists():
		raise FileNotFoundError(f"Directory {base_dir} does not exist.")
	delay = 0
	try:
		delay = float(argv[2])
	except:
		print("Invalid delay specified, defaulting to 0.")
	file_lock = Lock()
	single = SingularDiscovery(base_dir, file_lock, delay)
	split = SplitDiscovery(base_dir, file_lock, delay)
	pool = PoolDiscovery(base_dir, file_lock, delay)
	input()
	print("Shutting down...")
	single.stop()
	split.stop()
	pool.stop()