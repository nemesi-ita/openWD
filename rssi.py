# https://github.com/awkman/pywifi/blob/master/DOC.md

import pywifi
import math
import socket
from time import sleep
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from statistics import mean
import argparse
import os
import sys

def start():
    wifi = pywifi.PyWiFi()
    interfaces = wifi.interfaces()
    #print(interfaces[0])
    for i in interfaces:
        print(i)
        pass

    return interfaces[0]

def parse_nmea(data):
    gprmc_match = re.search(r'\$GPRMC,\d+\.\d+,[AV],(\d+\.\d+),([NS])(\d+\.\d+),([EW])(\d+\.\d+)', data)
    gpgga_match = re.search(r'\$GPGGA,\d+\.\d+,\d+\.\d+,[NS],\d+\.\d+,[EW],', data)
    
    if gprmc_match:
        latitude = float(gprmc_match.group(1))
        if gprmc_match.group(2) == 'S':
            latitude *= -1
        longitude = float(gprmc_match.group(3))
        if gprmc_match.group(4) == 'W':
            longitude *= -1
        return latitude, longitude
    elif gpgga_match:
        parts = data.split(',')
        latitude = float(parts[2])
        if parts[3] == 'S':
            latitude *= -1
        longitude = float(parts[4])
        if parts[5] == 'W':
            longitude *= -1
        return latitude, longitude
    else:
        return None

# PARAMETERS
'''
rssix[] --> Rssi ricevuti
positions[] --> Le mie posizioni (ancore)

'''
def trilateration_process(rssi_measurements, anchor_positions):
    # Dati di esempio
    #anchor_positions = np.array([[49, 51], [49, 51], [49, 51]])  # Posizioni delle 3 ancore
    #rssi_measurements = np.array([[-40, -37, -41]])  # Misurazioni RSSI (esempio con un singolo set di misurazioni)
    ple = 2.0  # Path Loss Exponent
    #rssi0 = -30  # Valore di riferimento del segnale RSSI a una distanza di riferimento
    rssi0 = mean(rssi_measurements)
    # Calcola le distanze stimare utilizzando il modello log-distanza
    estimated_distances = 10 ** ((rssi0 - rssi_measurements) / (10 * ple))
    
    # Calibra il modello log-distanza utilizzando una regressione lineare
    X = anchor_positions  # Posizioni delle ancore come variabili indipendenti
    y = estimated_distances.reshape(-1, 1)  # Distanze stimare come target
    regressor = LinearRegression().fit(X, y)

    # Stampa i coefficienti della regressione
    # Notare se il coefficiente varia (ci deve essere variazione nelle posizioni per il modello)
    print("Coefficiente del modello:", regressor.coef_)
    print("Intercezione del modello:", regressor.intercept_)
    

    # Ora puoi utilizzare il modello calibrato per stimare le distanze in base ai segnali RSSI misurati
    # Ad esempio, se hai nuove misurazioni RSSI, puoi usarle per stimare le distanze utilizzando il modello

    # Uso la formula log-distanza
    for d in rssi_measurements:
        print(f"Calcolo {d}: ", end='')
        distanza = 10**((rssi0-d)/(10*ple))
        print(distanza)
        

# Creazione e gestione argomenti da linea di comando
parser = argparse.ArgumentParser(usage=f"python3 {os.path.basename(sys.argv[0])} [-h/--help] -n/--network ", 
				description='Visualizza e traccia la tua rete wifi  ;)', 
                            	#add_help=False,
                            	epilog="Il telefono/trasmettitore NMEA e dispositivo di wardriving devono essere sulla stessa rete!")

parser.add_argument('-n', '--network', nargs="?", default=None, type=str, metavar="network", dest="network", 
                        help='Nome rete')

args = parser.parse_args()

IP = "192.168.43.144"
PORT = 2947

NETWORK = str(args.network)
if NETWORK is None:
    print("***ERRORE***\nNon e' stata selezionata una rete!")
    exit(1)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((IP, PORT))

iface = start()

def scanNet():
    iface.scan()
    sleep(2)
    scan_results = iface.scan_results()
    
    # Remove
    for net in scan_results:
        print(net)
        while net.signal is not None:
            if net.ssid == NETWORK:
                print(net.signal)
                return net.signal
            else:
                break


anchor = [[] for _ in range(3)]         # mia posizione gps
network_signals = {}    # dizionario che contiene {"ssid", [rssi1, rssi2, rssi3]}

signals = []    # array segnali RSSI
axy = []        # array x,y

# Salvo le tre potenze (in 3 punti diversi)
for i in range(3):
    parsed_data = None

    # Obtain new data
    strength = scanNet()

    # Salvo potenza nel momento X
    signals.append(strength)
    print(signals)
    
    # Ricevo posizione GPS
    while parsed_data is None:
        data, addr = s.recvfrom(2048)
        parsed_data = parse_nmea(data.decode())
        
    print(parsed_data)


    if parsed_data:
        x, y = parsed_data
        anchor[i] = (x, y)  # Assegna le coordinate (x, y) a anchor[i]
        #print(anchor[i])
    sleep(2)


network_signals.update({NETWORK: signals}) # Aggiorno le potenze della rete

# Output
'''
print("Ancore: ")
for i in anchor:
    print(i)

for j in network_signals.values():
    for i in j:
        print(i)
'''
# Trilaterazione
print(f'''
RSSI --> {np.array(network_signals.get(NETWORK))}
ANCORE --> {np.array(anchor)}
''')
trilateration_process(np.array(network_signals.get(NETWORK)), np.array(anchor)) 
'''
else:
        print("Nessuna rete trovata")
'''