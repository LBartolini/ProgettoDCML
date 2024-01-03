import multiprocessing
import os.path
import random
import subprocess
import tempfile
import threading
import time
from multiprocessing import Pool
from cpu_load_generator import load_all_cores

def current_ms():
    """
    Reports the current time in milliseconds
    :return: long int
    """
    return round(time.time() * 1000)

class LoadInjector:
    """
    Abstract class for Injecting Errors in the System probes
    """

    def __init__(self, tag: str = '', duration_ms: float = 1000):
        """
        Constructor
        """
        self.valid = True
        self.tag = tag
        self.duration_ms = duration_ms
        self.inj_thread = None
        self.completed_flag = True
        self.injected_interval = []
        self.init()

    def is_valid(self):
        return self.valid

    def init(self):
        """
        Override needed only if the injector needs some pre-setup to be run. Default is an empty method
        :return:
        """
        pass

    def inject_body(self):
        """
        Abstract method to be overridden
        """
        pass

    def inject(self):
        """
        Caller of the body of the injection mechanism, which will be executed in a separate thread
        """
        self.inj_thread = threading.Thread(target=self.inject_body, args=())
        self.inj_thread.start()

    def is_injector_running(self):
        """
        True if the injector has finished working (end of the 'injection_body' function)
        """
        return not self.completed_flag

    def force_close(self):
        """
        Try to force-close the injector
        """
        pass

    def get_injections(self) -> list:
        """
        Returns start-end times of injections exercised with this method
        """
        return self.injected_interval

    def get_name(self) -> str:
        """
        Abstract method to be overridden
        """
        return "[" + self.tag + "]Injector" + "(d" + str(self.duration_ms) + ")"

    @classmethod
    def fromJSON(cls, job):
        if job is not None:
            if 'type' in job:
                if job['type'] in {'Memory', 'RAM', 'MemoryUsage', 'Mem', 'MemoryStress'}:
                    return MemoryStressInjection.fromJSON(job)
                if job['type'] in {'Disk', 'SSD', 'DiskMemoryUsage', 'DiskStress'}:
                    return DiskStressInjection.fromJSON(job)
                if job['type'] in {'CPU', 'Proc', 'CPUUsage', 'CPUStress'}:
                    return CPUStressInjection.fromJSON(job)
        return None

class DiskStressInjection(LoadInjector):
    """
    DiskStress Error
    """

    def __init__(self, tag: str = '', duration_ms: float = 1000, n_workers: int = 10,
                 n_blocks: int = 10, rw_folder: str = './'):
        """
        Constructor
        """
        self.n_workers = n_workers
        self.n_blocks = n_blocks
        self.rw_folder = rw_folder
        self.poold = None
        LoadInjector.__init__(self, tag, duration_ms)

    def inject_body(self):
        """
        Abstract method to be overridden
        """
        self.completed_flag = False
        start_time = current_ms()
        self.poold = []
        poold_pool = Pool(self.n_workers)
        poold_pool.map_async(self.stress_disk, range(self.n_workers))
        self.poold.append(poold_pool)
        time.sleep((self.duration_ms - (current_ms() - start_time)) / 1000.0)
        if self.poold is not None:
            for pool_disk in self.poold:
                pool_disk.terminate()
        self.injected_interval.append({'start': start_time, 'end': current_ms()})
        self.completed_flag = True

    def force_close(self):
        """
        Try to force-close the injector
        """
        if self.poold is not None:
            for pool_disk in self.poold:
                pool_disk.terminate()
        self.completed_flag = True

    def stress_disk(self):
        block_to_write = 'x' * 1048576
        while True:
            filehandle = tempfile.TemporaryFile(dir=self.rw_folder)
            for _ in range(self.n_blocks):
                filehandle.write(block_to_write)
            filehandle.seek(0)
            for _ in range(self.n_blocks):
                content = filehandle.read(1048576)
            filehandle.close()
            del content
            del filehandle

    def get_name(self) -> str:
        """
        Abstract method to be overridden
        """
        return "[" + self.tag + "]DiskStressInjection" + "(d" + str(self.duration_ms) + "-nw" + str(
            self.n_workers) + ")"

    @classmethod
    def fromJSON(cls, job):
        return DiskStressInjection(tag=(job['tag'] if 'tag' in job else ''),
                                   duration_ms=(job['duration_ms'] if 'duration_ms' in job else 1000),
                                   n_workers=(job['n_workers'] if 'n_workers' in job else 10),
                                   n_blocks=(job['n_blocks'] if 'n_blocks' in job else 10))


class CPUStressInjection(LoadInjector):
    """
    CPUStress Error
    """

    def __init__(self, tag: str = '', duration_ms: float = 1000, target_load: int = 70):
        """
        Constructor
        """
        self.target_load = target_load
        LoadInjector.__init__(self, tag, duration_ms)

    def inject_body(self):
        """
        Abstract method to be overridden
        """
        self.completed_flag = False
        start_time = current_ms()
        load_all_cores(duration_s=self.duration_ms/1000,
                       target_load=self.target_load/100)
        self.injected_interval.append({'start': start_time, 'end': current_ms()})
        self.completed_flag = True

    def get_name(self) -> str:
        """
        Abstract method to be overridden
        """
        return "[" + self.tag + "]CPUStressInjection" + "(d" + str(self.duration_ms) + "-t"+str(self.target_load)+")"

    @classmethod
    def fromJSON(cls, job):
        return CPUStressInjection(tag=(job['tag'] if 'tag' in job else ''),
                                  duration_ms=(job['duration_ms'] if 'duration_ms' in job else 1000),
                                  target_load=(int(job['target_load']) if 'target_load' in job else 70))


class MemoryStressInjection(LoadInjector):
    """
    Loops and adds data to an array simulating memory usage
    """

    def __init__(self, tag: str = '', duration_ms: float = 1000, items_for_loop: int = 1234567):
        """
        Constructor
        """
        LoadInjector.__init__(self, tag, duration_ms)
        self.items_for_loop = items_for_loop
        self.force_stop = False

    def inject_body(self):
        """
        Abstract method to be overridden
        """
        self.completed_flag = False
        start_time = current_ms()
        my_list = []
        while True:
            my_list.append([999 for i in range(0, self.items_for_loop)])
            if current_ms() - start_time > self.duration_ms or self.force_stop:
                break
            else:
                time.sleep(0.001)

        self.injected_interval.append({'start': start_time, 'end': current_ms()})
        self.completed_flag = True
        self.force_stop = False

    def force_close(self):
        """
        Try to force-close the injector
        """
        self.force_stop = True

    def get_name(self) -> str:
        """
        Abstract method to be overridden
        """
        return "[" + self.tag + "]MemoryStressInjection(d" + str(self.duration_ms) + "-i" \
               + str(self.items_for_loop) + ")"

    @classmethod
    def fromJSON(cls, job):
        return MemoryStressInjection(tag=(job['tag'] if 'tag' in job else ''),
                                     duration_ms=(job['duration_ms'] if 'duration_ms' in job else 1000),
                                     items_for_loop=(job['items_for_loop']
                                                     if 'items_for_loop' in job else 1234567))