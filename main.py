# PYWIFI docu. --> https://github.com/awkman/pywifi/blob/master/DOC.md
# https://github.com/ifindev/indoor-positioning-algorithms


import socket
import re
import pywifi
from time import sleep
import argparse
import os.path
import sys
import subprocess
import math

network_signals = {}    # dizionario che contiene {"ssid": rssi_max}
network_positions = {}  # dizionario che contiene {"ssid": (posizione, distanza_minima)}


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


# Avvio la ricerca dei wifi
def scan_wifi(iface, s):
    attenuazione = 2
    iface.scan()  # Start scanning for WiFi networks
    scan_results = iface.scan_results()
    sleep(2)
    
    if not scan_results:
        print("Nessuna rete trovata...")
        return None
    
    print("WiFi networks found:")

    # sistemare ricezione di NMEA
    # capire se esiste un metodo per rssi e potenza
    for network in scan_results:
        ssid = network.ssid
        rssi =  network.signal
        potenza = -50     # Media dei router commerciali
        distance = distance_calc(rssi, potenza, attenuazione)

        if network_signals.get(ssid) is None or rssi > network_signals.get(ssid)[0]:
            network_signals.update({ssid: (rssi, potenza)}) # aggiorno le potenze

        parsed_position = None
        while parsed_position is None:
            data, addr = s.recvfrom(2048)
            parsed_position = parse_nmea(data.decode())
        network_positions.update({ssid: (parsed_position, distance)})

        print(f'''RETE --> {ssid}
              Potenza alle coordinate {network_positions.get(ssid)[0]} --> {network_signals.get(ssid)[0]}
              Distanza approssimata --> {network_positions.get(ssid)[1]}''')
        sleep(0.5)

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
