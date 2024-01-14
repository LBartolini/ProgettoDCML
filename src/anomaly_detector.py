import datetime
import pathlib
import pandas as pd
import time
import sys
from main_monitor_injector import monitor_system
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from joblib import load

def main(warning_threshold: int = 5):
    random_forest : RandomForestClassifier = load(str(pathlib.Path(__file__).parent.resolve())+'/random_forest.bin')
    standard_scaler : StandardScaler = load(str(pathlib.Path(__file__).parent.resolve())+'/standard_scaler.bin')

    time.sleep(0.5)
    warning_level: int = 0 # Keeps track of the warnings that the model catches
    last_printed_length: int = 0 # Value used to print blank spaces on top once the warning is cleared
    to_remove: int = 1 # Value used to increment exponentially the speed to which the anomaly detector goes back to normal after a warning
    with open(str(pathlib.Path(__file__).parent.resolve())+'/warnings.log', 'w') as log_file:
        while True:
            monitored_data = monitor_system()
            cols_to_drop = ['0irq', '0steal', '0guest', '0guest_nice', '0iowait',
                            '1irq', '1steal', '1guest', '1guest_nice', '1iowait',
                            '2irq', '2steal', '2guest', '2guest_nice', '2iowait',
                            '3irq', '3steal', '3guest', '3guest_nice', '3iowait',
                            '0min', '0max', '1min', '1max', '2min', '2max', '3min', '3max',
                            'time_s', 'virtual_total']
            monitored_data = pd.DataFrame([monitored_data]).drop(columns=cols_to_drop)
            
            X = standard_scaler.transform(monitored_data)
            is_anomaly = (random_forest.predict(X)[0]==1)

            if is_anomaly:
                warning_level += 1
                to_remove = 1 
            else:
                warning_level = max(warning_level-to_remove, 0)
                to_remove = to_remove*2 if warning_level>0 else 1 # Double the value or set to 0 if the warning level is already low
            
            if warning_level > warning_threshold:
                to_print=f'[{datetime.datetime.now()}] '+f'WARNING!!! (Level {warning_level})'
                last_printed_length = len(to_print)
            else:
                to_print = ' '*(last_printed_length+1)
                last_printed_length = 0

            print(to_print, end='\r', flush=True)
            if to_print[0]=='[':
                log_file.write(to_print+'\n')

            time.sleep(0.5)

if __name__ == '__main__':
    if len(sys.argv)>1:
        main(int(sys.argv[1])) # argv[1] is to set the threshold
    else:
        main()