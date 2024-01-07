import sys
import pathlib
import pandas as pd
import time
from main_monitor_injector import monitor_system
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from joblib import load

def main():
    random_forest : RandomForestClassifier = load(str(pathlib.Path(__file__).parent.resolve())+'/random_forest.bin')
    standard_scaler : StandardScaler = load(str(pathlib.Path(__file__).parent.resolve())+'/standard_scaler.bin')

    _ = monitor_system()
    time.sleep(0.5)

    while True: # WHILE
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
        anomaly_prob = random_forest.predict_proba(X)[0][1]

        print('WARNING!!!' if is_anomaly else '...', f' - Anomaly Probability={anomaly_prob:6.3f}')
        time.sleep(0.5)

if __name__ == '__main__':
    main()