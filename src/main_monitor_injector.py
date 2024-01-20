import csv
import os.path
import time
import psutil
from tqdm import tqdm
import json
import os.path
import random
from typing import List

from LoadInjector import LoadInjector

def read_injectors(json_object, inj_duration: int = 2, verbose: bool = True, n_inj: int = -1) -> List[LoadInjector]:
    """
    Method to read a JSON object and extract injectors that are specified there
    :param inj_duration: number of subsequent observations for which the injection takes place
    :param json_object: the json object or file containing a json object
    :param verbose: True is debug information has to be shown
    :param n_inj: -1 means the same injectors as in the json file, otherwise it is the number of injectors needed and are randomly inserted from the ones specified in the json
    :return: a list of available injectors
    """
    try:
        json_object = json.loads(json_object)
    except ValueError:
        if os.path.exists(json_object):
            with open(json_object) as f:
                json_object = json.load(f)
        else:
            print(f"Could not parse input {json_object}")
            json_object = None
    if json_object is None:
        raise json.JSONDecodeError("Unable to parse JSON")
    
    n_inj_parsed=len(json_object)
    if n_inj != -1 and n_inj < n_inj_parsed:
        raise ValueError("Param n_inj can't be lower than the number of injectors specified in the JSON file (n_inj can only be >= or exactly -1)")

    json_injectors = []
    for job in json_object:
        job["duration_ms"] = inj_duration
        new_inj = LoadInjector.fromJSON(job)
        if new_inj is not None and new_inj.is_valid():
            # Means it was a valid JSON specification of an Injector
            json_injectors.append(new_inj)
            if verbose: print(f'New injector loaded from JSON: {new_inj.get_name()}')
    
    inj_difference = n_inj-n_inj_parsed if n_inj != -1 else 0
    inj_to_add = []
    while inj_difference > 0:
        job = random.choice(json_object)
        new_inj = LoadInjector.fromJSON(job)
        if new_inj is not None and new_inj.is_valid():
            # Means it was a valid JSON specification of an Injector
            inj_to_add.append(new_inj)
            inj_difference -= 1
            if verbose: print(f'New injector loaded from JSON: {new_inj.get_name()}')

    return json_injectors+inj_to_add

def monitor_system() -> dict:
    """
    Method to monitor system
    :return: dictionary with informations about the system
    """
    ret_dict = {}

    cpu_times_percent = psutil.cpu_times_percent(interval=0.005, percpu=True)
    cpu_percent = psutil.cpu_percent(interval=0.05, percpu=True)
    cpu_freq = psutil.cpu_freq(percpu=True)
    virtual_memory = psutil.virtual_memory()._asdict() 

    ret_dict.update({str(i)+k: v for i, d in enumerate(cpu_times_percent) for k, v in d._asdict().items()})
    ret_dict.update({f'load{i}': v for i, v in enumerate(cpu_percent)})
    ret_dict.update({str(i)+k: v for i, d in enumerate(cpu_freq) for k, v in d._asdict().items()})
    ret_dict.update({'virtual_'+k:v for k, v in virtual_memory.items()})
    ret_dict['time_s'] = time.time()

    return ret_dict

def main(out_filename: str, obs_interval_sec: float, obs_per_inj: int, obs_between_inj: int, injectors: List[LoadInjector], verbose: bool = True) -> None:
    """
    Method to perform monitoring during various load tests
    :param out_filename: filename (as CSV) to log data read from monitoring the system
    :param obs_interval_sec: lenght in seconds for each observation
    :param obs_per_inj: number of observations during each injection
    :param obs_between_inj: number of observations between each injection, marked as 'rest' in the log file
    :param injectors: list of LoadInjectors to use for testing the system
    :return: nothing is returned
    """

    # Checking of out_filename already exists: if yes, delete
    if os.path.exists(out_filename):
        os.remove(out_filename)

    # Variable setup
    first_step = True
    inj_now = None
    obs_left_to_change = obs_between_inj

    # Monitoring Loop
    with open(out_filename, "a", newline="") as csvfile:
        #for obs_count in tqdm(range(max_n_obs), desc='Monitor Progress Bar'):
        while True:
            if obs_left_to_change<=0 and inj_now is None:
                # Start next Injection
                obs_left_to_change = obs_per_inj
                if len(injectors) == 0: 
                    break
                inj_now = injectors.pop(0)
                if verbose: print(f"{time.time()} | Injecting {inj_now.get_name()}|Inj remaining: {len(injectors)}")
                inj_now.inject()
            elif obs_left_to_change<=0 and inj_now is not None:
                # Pause from Injections
                if verbose: print(f"{time.time()}|Ending Injection")
                inj_now = None
                obs_left_to_change = obs_between_inj*random.choice([0.6, 0.8, 1, 1.2, 1.4]) # casually increment or decrement the length of the pause between injections

            start_time = time.time()
            data_to_log = monitor_system()
            data_to_log['injector'] = 'rest' if inj_now is None else inj_now.get_name() # add label column

            # Writing as a new line of a CSV file
            # Create a CSV writer using the field/column names
            writer = csv.DictWriter(csvfile, fieldnames=data_to_log.keys())
            if first_step:
                # Write the header row (column names)
                writer.writeheader()
                first_step = False
            writer.writerow(data_to_log)

            exe_time = time.time() - start_time
            if exe_time < obs_interval_sec:
                # Sleeping to synchronize to the obs-interval
                time.sleep(obs_interval_sec - exe_time)
            else:
                if verbose: print(f"[{inj_now.get_name() if inj_now is not None else 'Rest'}]Warning: execution of the monitor took too long (%.3f sec)" % (exe_time - obs_interval_sec))

            obs_left_to_change -= 1

if __name__ == '__main__':
    # General variables
    inj_json = 'base_injectors.json'
    time_step_sec = 0.5 # length of each monitoring step (in seconds)
    obs_per_inj = 80 # number of observations for each injection
    obs_between_inj = 140 # number of observations during rest phases
    n_injectors = 50 # number of injectors (if inj_json contains less, the injectors are duplicated randomly to reach goal number)

    # Extracting definitions of injectors from input JSON
    injectors = read_injectors(inj_json, 
                            inj_duration=obs_per_inj*time_step_sec*1000,
                            n_inj=n_injectors)
    random.shuffle(injectors)

    main(out_filename='output_folder/monitored_data.csv', 
        obs_interval_sec=time_step_sec,
        obs_per_inj=obs_per_inj,
        obs_between_inj=obs_between_inj,
        injectors=injectors)