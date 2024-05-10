import math
import pywifi
import time

def calcola_distanza(rssi, tx_power, n):
    # Calcola la distanza utilizzando la formula di calcolo della distanza RSSI
    # rssi: Potenza del segnale RSSI ricevuta
    # tx_power: Potenza di trasmissione del router (misurata in dBm)
    # n: Esponente di attenuazione del percorso, solitamente tra 2 e 4 (dipende dall'ambiente)
    
    # Calcola la distanza in metri
    distanza = 10 ** ((tx_power - rssi) / (10 * n))
    return distanza

def scan_wifi_networks():
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    
    iface.scan()
    time.sleep(2)  # Aspetta qualche secondo per permettere la scansione
    
    networks = iface.scan_results()
    return networks

def main():
    networks = scan_wifi_networks()
    if not networks:
        print("Nessuna rete WiFi trovata.")
        return
    
    tx_power = -50  # Supponiamo che la potenza di trasmissione del router sia -50 dBm
    n = 2  # Esponente di attenuazione del percorso
    
    print("Risultati della scansione delle reti WiFi:")
    for network in networks:
        ssid = network.ssid
        rssi = network.signal
        distance = calcola_distanza(rssi, tx_power, n)
        print("SSID: %s, RSSI: %d dBm, Distanza stimata: %.2f metri" % (ssid, rssi, distance))

if __name__ == "__main__":
    main()
