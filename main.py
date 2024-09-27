# PYWIFI docu. --> https://github.com/awkman/pywifi/blob/master/DOC.md
# https://github.com/ifindev/indoor-positioning-algorithms

import pywifi
from time import sleep
import argparse
import os.path
import sys
import subprocess
import serial

network_signals = {}    # dizionario che contiene {"ssid": rssi_max}
network_positions = {}  # dizionario che contiene {"ssid": ((latitude, longitude), minimum_distance)}

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

def start_GPS():
    # Configura la porta seriale (cambia con la tua porta o '/dev/ttyUSBX' su Linux)
    try:
        ser = serial.Serial('COM7', 9600, timeout=1)
        return ser
    except FileNotFoundError:
        print("Cannot find any NMEA device!!!") # Aggiungere
        exit(0)
    print("Stabilize connection between NMEA device and your device...")
    sleep(2)  # Attendi che la connessione seriale si stabilizzi


def distance_calc(rssi, tx_power, attenuazione):
    # Calcola la distanza utilizzando la formula di calcolo della distanza RSSI
    # rssi: Potenza del segnale RSSI ricevuta
    # tx_power: Potenza di trasmissione del router (misurata in dBm)
    # attenuazione: Esponente di attenuazione del percorso, solitamente tra 2 e 4 (dipende dall'ambiente)
    
    # Calcola la distanza in metri
    #distanza = 10 ** ((tx_power - rssi) / (10 * attenuazione))

    # Equazione di Friis
    distanza = 10 ** ((tx_power - rssi) / (20 * attenuazione))
    return distanza

def getPos():
    try:
        ser_iface.flush()
        lat = lon = alt = vel = sat = 0
        while True:
            sleep(0.5)
            if ser_iface.in_waiting > 0:  # Verifica se ci sono dati disponibili
                line = ser_iface.readline().decode().rstrip()  # Leggi e decodifica la linea NMEA
                
                if line.startswith('Lat '):
                    lat = line.split(' ')[1]
                elif line.startswith('Lon '):
                    lon = line.split(' ')[1]
                elif line.startswith('Alt '):
                    alt = line.split(' ')[1]
                elif line.startswith('Vel '):
                    vel = line.split(' ')[1]
                elif line.startswith('Sat '):
                    sat = line.split(' ')[1]
                elif line.startswith("END"):
                    return lat, lon, alt, vel, sat
                else:
                    continue
    except Exception as e:
        print(e)

# Avvio la ricerca dei wifi
def scan_wifi(iface):
    attenuazione = 2
    iface.scan()  # Start scanning for WiFi networks
    sleep(2)
    scan_results = iface.scan_results()
    
    
    if not scan_results:
        print("Nessuna rete trovata...")
        return None
    
    print("WiFi networks found:")

    # capire se esiste un metodo per rssi e potenza
    latitude, longitude, altitude, velocity, satellites = getPos()
    for network in scan_results:
        ssid = network.ssid
        rssi =  network.signal
        potenza = -50     # Media dei router commerciali
        distance = distance_calc(rssi, potenza, attenuazione)

        if network_signals.get(ssid) is None or rssi > network_signals.get(ssid)[0]:
            network_signals.update({ssid: (rssi, potenza)}) # aggiorno le potenze

        network_positions.update({ssid: ((latitude, longitude), distance)})

        print(f'''NETWORK --> {ssid}
              Signal strength at coordinates {network_positions.get(ssid)[0]} --> {network_signals.get(ssid)[0]}
              Distance --> {network_positions.get(ssid)[1]}''')

# Configurazione interfacce
iface = start_WIFI()
ser_iface = start_GPS()

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

    # Funzione di validazione per l'estensione
    def validate_extension(extension):
        if extension is None:
            raise argparse.ArgumentTypeError(f"Estensione non configurata.")
        valid_extensions = ['t', 'T', 'txt', 'TXT', 'c', 'C', 'csv', 'CSV']
        if extension not in valid_extensions:
            raise argparse.ArgumentTypeError(f"Estensione non valida. \nEstensioni accettate: {', '.join(valid_extensions)}.")
        return extension


    # Creazione e gestione argomenti da linea di comando
    parser = argparse.ArgumentParser(usage=f"python3 {os.path.basename(sys.argv[0])} [-h] [-a ADDRESS] [-e EXTENSION]", 
                                    description='Visualizza e traccia le reti wifi nella tua zona con coordinate GPS e client connessi! ;)', 
                                    add_help=False,
                                    epilog="Ensure the serial port is correct!")

    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help="Show this help message")

    parser.add_argument('-e', '--export', nargs="?", default='csv', type=str, metavar="EXTENSION", dest="export", 
                        help='Seleziona il formato di esportazione. Default .CSV')
    # Aggiungere opzione per visualizzare il file su mappa
    
    try:
        args = parser.parse_args()
        validate_extension(args.export)
        
    except Exception as e:
        print(f"\n\n\t\t**ERRORE**\n\n{e}")
        return 1
    
    print("Waiting NMEA data...")  
    while True:
        scan_wifi(iface)
        sleep(0.2)
        

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
    finally:
        ser_iface.close()
    
    print("\n\n\t\t openWD by #NEMESI-ITA#")