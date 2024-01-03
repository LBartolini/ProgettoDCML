import threading
import time
import random
from cpu_load_generator import load_all_cores, load_single_core

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
                if job['type'] in {'CPU', 'Proc', 'CPUUsage', 'CPUStress'}:
                    return CPUStressInjection.fromJSON(job)
        return None


class CPUStressInjection(LoadInjector):
    """
    CPUStress Error
    """

    def __init__(self, tag: str = '', duration_ms: float = 1000, target_load: int = 70, target_core: int = -1):
        """
        Constructor
        """
        self.target_load = int(target_load*random.choice([0.9, 1, 1.1]))
        self.target_core = target_core
        LoadInjector.__init__(self, tag, duration_ms)

    def inject_body(self):
        """
        Abstract method to be overridden
        """
        self.completed_flag = False
        start_time = current_ms()

        if self.target_core == -1:
            load_all_cores(duration_s=self.duration_ms/1000,
                       target_load=self.target_load/100)
        else:
            load_single_core(core_num=self.target_core, 
                             duration_s=self.duration_ms/1000,
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
                                  target_load=(job['target_load'] if 'target_load' in job else 70),
                                  target_core=(job['target_core'] if 'target_core' in job else -1))

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
            my_list.append([999 for _ in range(self.items_for_loop)])
            if current_ms() - start_time > self.duration_ms or self.force_stop:
                break
            else:
                time.sleep(0.0001)

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