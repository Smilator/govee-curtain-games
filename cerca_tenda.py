"""Controlla se il computer vede la tenda via Bluetooth.

    python cerca_tenda.py

Elenca i dispositivi Govee vicini. La tenda compare come "Govee_H70B4_xxxx".
"""
import asyncio

from bleak import BleakScanner


async def main():
    print("cerco per 12 secondi...")
    found = await BleakScanner.discover(timeout=12, return_adv=True)
    govee = sorted(((adv.rssi, d.name or adv.local_name) for d, adv in found.values()
                    if "Govee" in (d.name or adv.local_name or "")), reverse=True)
    for rssi, name in govee:
        mark = "  <-- la tenda" if "H70B4" in name else ""
        print(f"{name}   segnale {rssi}{mark}")
    if not any("H70B4" in n for _, n in govee):
        print("Tenda H70B4 non trovata: vedi 'Problemi comuni' nel README.")


asyncio.run(main())
