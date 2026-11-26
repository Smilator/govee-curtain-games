# Giochi sulla tenda LED Govee H70B4

Tre giochi classici, **Snake**, **Arkanoid** e **Pong**, da giocare sulla tenda LED Govee H70B4 (40x26 pixel) dal Terminale del computer.
Il gioco si comanda dalla tastiera. Ogni fotogramma viene mandato alla tenda via Bluetooth, mentre nel Terminale c'è un'anteprima a colori.

Provato su macOS con Python 3.9.

## Avvio in 5 passi

1. **Scarica il progetto e installa l'unica dipendenza** ([bleak](https://github.com/hbldh/bleak), per il Bluetooth):

   ```bash
   git clone https://github.com/Smilator/govee-curtain-games.git
   cd govee-curtain-games
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Dai il permesso Bluetooth al Terminale.** Su macOS vai in *Impostazioni di Sistema → Privacy e sicurezza → Bluetooth* e attiva l'app Terminale. Di solito macOS lo chiede da solo al primo avvio.

3. **Prepara la tenda.** Deve essere accesa e a pochi metri dal computer. **Chiudi del tutto l'app Govee sul telefono**: la tenda accetta un solo collegamento Bluetooth alla volta.

4. **Controlla che il computer veda la tenda:**

   ```bash
   .venv/bin/python cerca_tenda.py
   ```

   Nell'elenco deve comparire `Govee_H70B4_xxxx  <-- la tenda`.

5. **Gioca:**

   ```bash
   .venv/bin/python snake.py
   .venv/bin/python arkanoid.py
   .venv/bin/python pong.py
   ```

Il Terminale deve essere largo almeno 82 colonne e alto almeno 30 righe, altrimenti l'anteprima viene tagliata. Si esce con `q`.

## Comandi

| Gioco | Tasti | Regole |
|---|---|---|
| Snake | frecce | Mangia il cibo rosso; i bordi fanno da tunnel. Più mangi, più va veloce. |
| Arkanoid | frecce ← →, spazio per lanciare la palla | 3 vite, i puntini rossi in alto. Finiti i mattoni si passa al livello dopo. |
| Pong | frecce ↑ ↓ | Tu sei a sinistra, il computer a destra. Vince chi arriva a 5. |

In tutti i giochi il punteggio è in alto al centro. Quando la partita finisce parte un'animazione e si riparte da zero.

## Opzioni

Si aggiungono in fondo al comando, per esempio `.venv/bin/python snake.py --solo-schermo`.

| Opzione | Effetto |
|---|---|
| `--solo-schermo` | Gioca senza tenda, solo con l'anteprima nel Terminale. |
| `--non-specchiare` | Non gira l'immagine destra/sinistra. Usala se sulla tenda il punteggio si legge al contrario. |
| `--specchia-verticale` | Gira l'immagine sopra/sotto. Usala se sulla tenda il punteggio è in basso. |

## Problemi comuni

- **"tenda non trovata"**
  1. Stacca la tenda dalla corrente per 10 secondi e riattaccala.
  2. Avvicinati e controlla che l'app Govee sia chiusa.
  3. Se ancora non compare, spegni e riaccendi il Bluetooth del computer.

  Dopo che un gioco si è chiuso male, la tenda può restare invisibile per un po': in quel caso aiuta staccarla dalla corrente.
- **"Bluetooth device is turned off" o chiusura immediata.** Il Terminale non ha il permesso Bluetooth: vedi il passo 2. Avvia i giochi dall'app Terminale di macOS.
- **La tenda resta ferma o spenta.** Esci con `q`, stacca e riattacca la tenda, poi rilancia il gioco.
- **Lo sfondo non è nero.** La tenda non spegne del tutto il nero, quindi i giochi usano il blu più scuro possibile. Puoi cambiarlo con la costante `BG` in `tenda.py`.

## Come funziona

Tutta la parte tecnica è in `tenda.py`. I giochi disegnano soltanto: ogni gioco produce un'immagine 40x26 a ogni passo.

1. **Collegamento.** Il computer si collega alla tenda via Bluetooth Low Energy e fa l'handshake con la chiave fissa del protocollo Govee. È pubblica e uguale per tutti i dispositivi, non è una chiave privata. Da lì riceve una chiave di sessione, che cifra tutti i pacchetti successivi: AES-128-ECB sui blocchi da 16 byte, RC4 sui byte restanti. L'AES usa il comando `openssl`, già presente su macOS e Linux.
2. **Immagine.** Ogni fotogramma diventa un PNG 40x26, nello stesso formato usato dall'app Govee. Viene diviso in pacchetti da massimo 509 byte e seguito dal comando che lo mostra. Il gioco aspetta la conferma della tenda prima di mandare il fotogramma successivo, per circa 5–8 fotogrammi al secondo.
3. **Gioco.** `play()` legge la tastiera, fa avanzare il gioco, aggiorna l'anteprima nel Terminale e la tenda.

Per creare un nuovo gioco basta una classe con `title`, `help`, `tick`, `over`, `key(k)`, `step()`, `pixels()`, `end_animation()`, `reset()` e `score_text()`, passata a `play()`. Il gioco più corto da usare come modello è `snake.py`.

## Avvertenze

Progetto amatoriale, non affiliato a Govee. Il protocollo è stato ricostruito osservando il traffico Bluetooth dell'app ufficiale. Funziona con la H70B4; altri modelli di tende Govee potrebbero richiedere modifiche.

## Licenza

MIT, vedi il file `LICENSE`.
