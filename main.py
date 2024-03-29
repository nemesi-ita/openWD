# PYWIFI docu. --> https://github.com/awkman/pywifi/blob/master/DOC.md


import socket
import re
import pywifi
from pywifi import const
from time import sleep
import argparse
import os.path
import sys
import subprocess

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

    print("Interfacce disponibili: \n")
    for i, iface in enumerate(interfaces):
        print(f"{i}: {iface.name()} | Chipset: {get_interface_info(iface.name())}")

    interfaceIndex = int(input("Selezione l'interfaccia che desideri utilizzare: "))
    wifi_interface = interfaces[interfaceIndex]

    return wifi_interface

# Avvio la ricerca dei wifi
def scan_wifi(iface):
    iface.scan()  # Start scanning for WiFi networks
    scan_results = iface.scan_results()

    print("WiFi networks found:")
    # Aggiungere un dizionario per tenere traccia delle reti e del RSSI
    for network in scan_results:
        print("SSID:", network.ssid, "Signal Strength:", network.signal)

def init():
    # Creazione e gestione argomenti da linea di comando
    parser = argparse.ArgumentParser(usage=f"python3 {os.path.basename(sys.argv[0])} [-h] [-p PORT] [-a ADDRESS]", 
                                    description='Visualizza e traccia le reti wifi nella tua zona con coordinate GPS e client connessi! ;)', 
                                    add_help=False,
                                    epilog="Il telefono/trasmettitore NMEA e dispositivo di wardriving devono essere sulla stessa rete!")

    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help="Mostra questo messaggio di aiuto")
    parser.add_argument('-p', '--port', type=int, default=2947, help='Porta di ricezione delle coordinate GPS. Default: 2947')
    parser.add_argument('-a', '--address', type=str, default='0.0.0.0', help='Indirizzo IP di ricezione. Default: 0.0.0.0')
    # Aggiungere argomento per export (csv, txt)
    # Aggiungere opzione per visualizzare il file su mappa
    args = parser.parse_args()

    UDP_IP = args.address
    UDP_PORT = args.port
    # Configura il socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    # Configurazione interfaccia wireless
    iface = start_WIFI()

    print(f"In ascolto sul socket: {args.address}:{args.port}\nIn attesa di dati da GPSDForwarder...")

    while True:
        try:
            # Ricevi i dati
            data, addr = sock.recvfrom(1024)  
            parsed_data = parse_nmea(data.decode())

            if parsed_data:
                scan_wifi(iface)
                latitude, longitude = parsed_data
                print("Latitudine:", latitude)
                print("Longitudine:", longitude)
                
                sleep(1)
        except KeyboardInterrupt:
            print("Saving and exit!")
            #exportData()
            break

if __name__ == "__main__":
    init()
    print("openWD by #N3m3s1#")