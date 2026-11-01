# IRREGULAR RANGE – Simple-Past-Schießstand

Ein kleines, komplett mausgesteuertes Lernspiel für Windows. **28 unregelmäßige
Verben** aus drei abfotografierten Schulbuchseiten treffen auf **280 verschiedene
Munitions-Upgrades**. Keine Werbung, keine Accounts, keine Online-Verbindung.

## Windows-EXE herunterladen

1. Hier im Repository den Reiter **Actions** öffnen.
2. Den neuesten erfolgreichen Lauf **Windows EXE** auswählen.
3. Unter **Artifacts** `IrregularRange-Windows` herunterladen und entpacken.
4. `IrregularRange.exe` starten (ggf. Windows-SmartScreen-Hinweis für eine
   selbst erstellte, unsignierte EXE bestätigen, wenn du der Quelle vertraust).

Die EXE wird automatisch bei relevanten Änderungen am `main`-Branch erzeugt.
Alternativ lässt sich der Build bewusst über **Run workflow** starten.
Das Artifact bleibt 7 Tage verfügbar; erneutes Bauen nur bei Bedarf.

## Spielprinzip

- Pro Frage erscheint eine englische Grundform, etwa **go**.
- Drei Papp-Dummys klappen hoch: z. B. **go**, **went**, **goed**.
- Innerhalb von **5 Sekunden** das richtige Simple Past mit der **linken
  Maustaste** treffen. Danebenschießen, falsch treffen oder Zeitablauf kostet
  **genau ein Leben**. Du startest mit fünf Leben.
- Nach Fehlern wird die korrekte Antwort groß eingeblendet.
- Richtige Treffer bringen Münzen; schnellere Treffer und Serien mehr.
- **Jeder Run hat ein klares Ziel:** alle **28 unterschiedlichen Verben**
  mindestens einmal richtig beantworten. Richtige Antworten verlassen den
  Stapel; falsche Antworten und Zeitüberschreitungen kommen später erneut.
- Nach jeder Frage **außer der letzten erfolgreichen** öffnet der Shop.
  Kaufbare Verbesserungen bleiben dauerhaft freigeschaltet und lassen sich
  immer wieder ausrüsten.
- **Garantiert kostenlos:** In jedem Shop gibt es eine Probepatrone für die
  nächste Frage. Damit steht auch bei **0 Münzen** eine Upgrade-Option offen.
- Nach dem fünften Fehlversuch ist der Run verloren. Werden alle 28 Verben
  richtig beantwortet, endet der Run mit einer **Extra-Münzprämie**:
  **1.800 Münzen bei null Fehlern**, minus **300 pro Fehler** (bei ein bis vier
  Fehlern: 1.500 / 1.200 / 900 / 600). Die Prämie wird nur einmal ausgezahlt.
  Abschlüsse und der beste Run bleiben gespeichert.

## 280 Upgrades

Es gibt **28 Munitionsfamilien mit je 10 Stufen**. Darunter: Feuerwerk,
Explosion, Fußball, Laser, Seifenblasen, Raketen, Schneebälle, Galaxien,
Pizzas und Kometen. Die Familien haben nicht nur unterschiedliche Geschosse, sondern jeweils
**eigene Flugbahnen, Leuchtspuren und Einschlaganimationen**. Laser schießen
Lichtstrahlen, Fußballtore erscheinen als Netze, Explosionen als Comic-Bursts,
Feuerwerk als vielfarbige Himmelssterne und Seifenblasen schweben nach oben.
Höhere Stufen verstärken Spuren, Splitter, Stoßwellen und Bühneneffekte. 280 Einträge sind einzeln kaufbar. Über die Shop-Pfeile sind
alle erreichbar, ohne dass der Shop von Anfang an alles kostenlos macht.

Die Fortschrittsdatei liegt unter
`%APPDATA%\IrregularRange\progress.json` (Windows) bzw.
`~/.local/share/irregular_range/progress.json` (Linux).

## Verben aus den Fotos

**Aufgabe 7 / Hauptliste (21):**
`be, become, bring, buy, come, do, drink, eat, get, go, give, have, keep,
make, meet, put, run, say, speak, tell, wear`

**Weitere Übungen/Anweisungen (7):**
`think, sell, sleep, know, choose, write, hear`

Die eindeutigen Simple-Past-Lösungen und bewusst falschen Alternativen stehen
mit ihrer Fundstelle in [`vocabulary.py`](vocabulary.py). Bei **be** steht
`was / were` gemeinsam auf einem Ziel, weil beide Formen richtig sind; bei
**put** wird die unveränderte Form nicht als Fehler gewertet.

## Lokal ausführen / weiterentwickeln

Python 3.11 oder neuer:

```bash
python -m pip install -r requirements.txt
python game.py
python -m unittest discover -s tests -v
```

**GUI-Schnelltest** (bei Bedarf mit SDL-Dummy-Treiber):

```bash
python game.py --smoke-test
```

**Windows-EXE lokal bauen:**

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name IrregularRange game.py
```

Die Grafik und Sounds werden zur Laufzeit ohne externe Assets erzeugt. Die
Tests prüfen den endlichen Run, wiederholte falsche Verben, einmalige Bonus-
Auszahlung und alle 28 animierten Waffenfamilien. Der GitHub-Workflow testet
zusätzlich ein paar Spielbilder ohne sichtbares Fenster. Er nutzt nur einen Windows-Job, läuft nicht bei Pull-Requests
oder reinen README-Änderungen, vermeidet doppelte laufende Builds und lädt
nur das fertige `.exe` als Artifact hoch. Das hält die Actions-Kosten gering.


## Grafikdesign und Schriftarten

Das dunkelblaue Neon-Layout orientiert sich an den Referenz-Screenshots: 
Hintergrund `#060914`, Panels `#121A36`, Cyan `#22E6FF`,
Treffer-Lime `#B6FF3B`, Gold `#FFC53D`, Combo-Orange `#FF7A1A`.
Schwebende Ziele und Kreis-Timer sind exakt auf ihre Maus-Hitboxen abgestimmt.
Die visuellen Effekte bleiben innerhalb der Spielflaeche und verdecken keine Texte,
Schaltflaechen oder HUD-Panels.

Die drei Schriften **Russo One**, **Chakra Petch** und **Orbitron** werden bei
GitHub Actions automatisch aus dem offiziellen Google-Fonts-Repository geladen
und in die eigenstaendige Windows-EXE eingebettet. Die zugehoerigen
SIL-OFL-Lizenzdateien werden ebenfalls eingebettet. Es muss nichts nachinstalliert
werden. Ohne die Dateien verwendet der lokale Quellcode gut lesbare
System-Schriftarten.

Der guenstige Ubuntu-Workflow `Visual QA` erzeugt fuer die Designpruefung
fuenf Pygame-Screenshots. Fuer fertige Windows-Builds wird nur der
`Windows EXE`-Workflow auf `main` verwendet.
