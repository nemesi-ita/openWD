import pywifi
import math
import socket
from time import sleep
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from statistics import mean

def start():
    wifi = pywifi.PyWiFi()
    interfaces = wifi.interfaces()
    print(interfaces[0])
    for i in interfaces:
        print(i)

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
    '''
    # Supponiamo che "anchor" sia una lista di tuple contenenti le coordinate (x, y) dei punti di ancoraggio
    # e "distances" sia una lista contenente le distanze misurate dai punti di ancoraggio all'oggetto
    
    # Assicuriamoci che ci siano abbastanza coordinate di ancoraggio e distanze
    if len(anchor) < 3 or len(distances) < 3:
        print("Non ci sono abbastanza punti di ancoraggio o distanze per eseguire la trilaterazione.")
        return None
    
    # Estraiamo le coordinate x e y dei punti di ancoraggio
    xa, ya = anchor[0]
    xb, yb = anchor[1]
    xc, yc = anchor[2]
    
    # Estraiamo le distanze misurate
    ra, rb, rc = distances[0], distances[1], distances[2]
    
    # Calcoliamo le differenze di coordinate tra i punti di ancoraggio
    #dx1 = xb - xa
    #dy1 = yb - ya
    #dx2 = xc - xa
    #dy2 = yc - ya
    # Calcola le differenze di coordinate tra i punti di ancoraggio (utilizzando valori assoluti)
    dx1 = abs(xb - xa)
    dy1 = abs(yb - ya)
    dx2 = abs(xc - xa)
    dy2 = abs(yc - ya)
    
    # Calcoliamo la differenza tra le distanze misurate al quadrato
    dr1_sq = rb**2 - ra**2
    dr2_sq = rc**2 - ra**2
    
    # Calcoliamo il coefficiente della formula di trilaterazione
    D = 2 * (dx1 * dy2 - dx2 * dy1)
    print("D --> ", D)
    # Calcoliamo le coordinate x e y dell'oggetto
    x = (dr1_sq * dy2 - dr2_sq * dy1) / D
    y = (dr2_sq * dx1 - dr1_sq * dx2) / D
    
    return x, y

def calculate(anchor, rssi_values):
    # Assicuriamoci che ci siano abbastanza coordinate di ancoraggio e RSSI
    print(rssi_values)
    if len(anchor) < 3 or len(rssi_values) < 3:
        print("Non ci sono abbastanza punti di ancoraggio o RSSI per eseguire la trilaterazione.")
        return None
    
    # Mappa RSSI ai valori di distanza utilizzando un modello di propagazione empirico
    distances = rssi_values #map_rssi_to_distance(rssi_values)
    
    # Esegui la trilaterazione con le distanze calcolate
    return trilaterate(anchor, distances)'''

IP = "192.168.1.100"
PORT = 2947
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((IP, PORT))

iface = start()


iface.scan()  # Start scanning for WiFi networks
scan_results = iface.scan_results()

anchor = [[] for _ in range(3)]         # mia posizione gps
network_signals = {}    # dizionario che contiene {"ssid", [rssi1, rssi2, rssi3]}
# Ricevi i dati

for network in scan_results:
    signals = []    # array segnali RSSI
    axy = []        # array x,y
    if network.ssid == "FASTWEB-1-5968F3":
        print("SSID:", network.ssid, "Signal Strength:", network.signal)

        # Salvo le tre potenze (in 3 punti diversi)
        for i in range(3):
            parsed_data = None
            signals.append(network.signal)

            while parsed_data is None:
                data, addr = s.recvfrom(2048)
                parsed_data = parse_nmea(data.decode())
                
            print(parsed_data)


            if parsed_data:
                x, y = parsed_data
                anchor[i] = (x, y)  # Assegna le coordinate (x, y) a anchor[i]
                #print(anchor[i])
            sleep(2)


        network_signals.update({network.ssid: signals}) # Aggiorno le potenze

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
        RSSI --> {np.array(network_signals.get(network.ssid))}
        ANCORE --> {np.array(anchor)}
        ''')
        trilateration_process(np.array(network_signals.get(network.ssid)), np.array(anchor)) 

        break