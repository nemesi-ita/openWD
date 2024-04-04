# PYWIFI docu. --> https://github.com/awkman/pywifi/blob/master/DOC.md
# https://github.com/ifindev/indoor-positioning-algorithms


import socket
import re
import pywifi
from pywifi import const
from time import sleep
import argparse
import os.path
import sys
import subprocess
import math
import numpy as np
from sklearn.linear_model import LinearRegression
from statistics import mean

anchor = [[] for _ in range(3)]         # mia posizione gps
network_signals = {}    # dizionario che contiene {"ssid": [rssi1, rssi2, rssi3]}
network_positions = {}  # dizionario che contiene {"ssid": distanza}


# Trovo le corrispondenze gps
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

# Avvio l'interfaccia corretta
def start_WIFI():
    # Sistemare getChipset
    def get_interface_info(interface):
        try:
            proc = subprocess.Popen(['iw', 'dev', interface, 'info'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = proc.communicate()
            out = out.decode('utf-8').strip().split('\n')
            chipset = None
            for line in out:
                if 'driver' in line:
                    chipset = line.split()[-1]
                    break
            return chipset
        except Exception as e:
            print(f"Errore durante il recupero delle informazioni sull'interfaccia {interface}: {e}")
            return None

    wifi = pywifi.PyWiFi()
    interfaces = wifi.interfaces()

    print("Interfacce disponibili per l'ascolto: \n")
    for i, iface in enumerate(interfaces):
        print(f"{i}: {iface.name()} | Chipset: {get_interface_info(iface.name())}\n")

    interfaceIndex = int(input("Interfaccia >> "))
    wifi_interface = interfaces[interfaceIndex]

    return wifi_interface


def trilateration_process(rssi_measurements, anchor_positions):
    distance = None
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
        distance = 10**((rssi0-d)/(10*ple))
        print(distance)
    
    return distance

# Avvio la ricerca dei wifi
def scan_wifi(iface, s):
    iface.scan()  # Start scanning for WiFi networks
    scan_results = iface.scan_results()

    print("WiFi networks found:")
    # Aggiungere un dizionario per tenere traccia delle reti e del RSSI
    for network in scan_results:
        signals = []    # sengali RSSI
        axy = []        # array x, y

        # Print new networks
        if network.ssid not in network_signals.keys():
            print("SSID:", network.ssid, "Signal Strength:", network.signal)

        for i in range(3):
            parsed_data = None
            signals.append(network.signal)

            while parsed_data is None:
                data, addr = s.recvfrom(2048)
                parsed_data = parse_nmea(data.decode())
            # if parsed_data:
            x, y = parsed_data
            anchor[i] = (x, y)  # aggiungo l'ancora con le mie coordinate attuali
            sleep(1)

        network_signals.update({network.ssid: signals}) # aggiorno le potenze
        distance = trilateration_process(np.array(network_signals.get(network.ssid)), np.array(anchor))
        network_positions.update({network.ssid: distance})

        


def init():
    print('''
                  _-o#&&*\'\'\'\'?d:>b\_
              _o/"`''    '',, dWF9WIFIHo_
           .o&#'        `"WbHWiFiWiFiWiFHo.
         .o"" '         vodW*$&&HWiFiWiFiWi?.
        ,'              $W&ood,~'`(&##WiFiWiH\\
       /               ,WiFiWiF#b?#WiFiWiFiWiFL
      &              ?WiFiWiFiWiFiWiFiW7WiF$R*Hk
     ?$.            :WiFiWiFiWiFiWiFiWiF/HWiF|`*L
    |               |WiFiWiFiWiFiWiFiWiFibWH'   T,
    $H#:            `*WiFiWiFiWiFiWiFiWiFib#}'  `?
    ]WiH#             ""*""""*#WiFiWiFiWiFiW'    -
    WiFiWb_                   |WiFiWiFiWiFP'     :
    HWiFiWiFio                 `WiFiWiFiWT       .
    ?WiFiWiFiP                  9WiFiWiFi}       -
    -?WiFiWiF                  |WiFiWiFiW?,d-    '
    :|WiFiWi-                 `WiFiWiFT .M|.   :
      .9WiF[                    &WiFiW*' `'    .
       :9Wik                    `WiF#"        -
         &W}                     `          .-
          `&.                             .
            `~,   .                     ./
                . _                  .-
                  '`--._,dd###pp=""'
    ''')

    # Funzione di validazione per la porta
    def validate_port(port):
        if port is None:
            raise argparse.ArgumentTypeError(f"Porta non configurata.")
        if not 0 <= port <= 65535:
            raise argparse.ArgumentTypeError(f"La porta deve essere compresa tra 0 e 65535.")
        return port

    # Funzione di validazione per l'IP
    def validate_ip(ip):
        if ip is None:
            raise argparse.ArgumentTypeError(f"IP non configurato.")

        chunks = ip.split('.')
        if len(chunks) != 4:
            raise argparse.ArgumentTypeError("L'IP deve avere 4 chunk separati da punti.")
        for chunk in chunks:
            if not 0 <= int(chunk) <= 255:
                raise argparse.ArgumentTypeError(f"Chunk di IP non valido: *{chunk}* \nDeve essere compreso tra 0 e 255.")
        return ip

    # Funzione di validazione per l'estensione
    def validate_extension(extension):
        if extension is None:
            raise argparse.ArgumentTypeError(f"Estensione non configurata.")
        valid_extensions = ['t', 'T', 'txt', 'TXT', 'c', 'C', 'csv', 'CSV']
        if extension not in valid_extensions:
            raise argparse.ArgumentTypeError(f"Estensione non valida. \nEstensioni accettate: {', '.join(valid_extensions)}.")
        return extension


    # Creazione e gestione argomenti da linea di comando
    parser = argparse.ArgumentParser(usage=f"python3 {os.path.basename(sys.argv[0])} [-h] [-p PORT] [-a ADDRESS] [-e EXTENSION]", 
                                    description='Visualizza e traccia le reti wifi nella tua zona con coordinate GPS e client connessi! ;)', 
                                    add_help=False,
                                    epilog="Il telefono/trasmettitore NMEA e dispositivo di wardriving devono essere sulla stessa rete!")

    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help="Mostra questo messaggio di aiuto")
    parser.add_argument('-p', '--port', nargs="?", default=2947, type=int, metavar="PORT", dest="port", 
                        help='Porta di ricezione delle coordinate GPS. Default: 2947')

    parser.add_argument('-a', '--address', nargs="?", default='0.0.0.0', type=str, metavar="IP", dest="address", 
                        help='Indirizzo IP di ricezione. Default: 0.0.0.0')

    parser.add_argument('-e', '--export', nargs="?", default='csv', type=str, metavar="EXTENSION", dest="export", 
                        help='Seleziona il formato di esportazione. Default .CSV')
    # Aggiungere opzione per visualizzare il file su mappa
    
    try:
        args = parser.parse_args()
        validate_port(args.port)
        validate_ip(args.address)
        validate_extension(args.export)

        UDP_IP = args.address
        UDP_PORT = args.port

        # Configura il socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"\n\n\t\t**ERRORE**\n\n{e}")
        return 1
        
        
    # Configurazione interfaccia wireless
    iface = start_WIFI()
    print(f"In ascolto sul socket: {args.address}:{args.port}\nIn attesa di dati da GPSDForwarder...")

    while True:
        scan_wifi(iface, sock)
        '''
        try:
            # Ricevi i dati GPS (ASYNC)
            data, addr = sock.recvfrom(2048)  
            parsed_data = parse_nmea(data.decode())

            if parsed_data:
                scan_wifi(iface)
                latitude, longitude = parsed_data
                print("Latitudine:", latitude)
                print("Longitudine:", longitude)
                
        except KeyboardInterrupt:
            print("Saving and exit!")
            #exportData()
            break
        '''

if __name__ == "__main__":
    try:
        init()
    except KeyboardInterrupt:
        print('''\n\n
            __..--''``---....___   _..._    __
 /// //_.-'    .-/";  `        ``<._  ``.''_ `. / // /
///_.-' _..--.'_    \      Ctrl+c        `( ) ) // //
/ (_..-' // (< _     ;_..__               ; `' / ///
 / // // //  `-._,_)' // / ``--...____..-' /// / //
        ''')
    print("\n\n\t\topenWD by #N3m3s1#")
