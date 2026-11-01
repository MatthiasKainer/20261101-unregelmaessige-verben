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
- **Nach jeder Frage** öffnet der Shop. Kaufbare Verbesserungen bleiben
  dauerhaft freigeschaltet und lassen sich immer wieder ausrüsten.
- **Garantiert kostenlos:** In jedem Shop gibt es eine Probepatrone für die
  nächste Frage. Damit steht auch bei **0 Münzen** eine Upgrade-Option offen.
- Nach dem fünften Fehlversuch startet auf Wunsch ein neuer Durchgang.

## 280 Upgrades

Es gibt **28 Munitionsfamilien mit je 10 Stufen**. Darunter: Feuerwerk,
Explosion, Fußball, Laser, Seifenblasen, Raketen, Schneebälle, Galaxien,
Pizzas und Kometen. Die Familien haben eigene gezeichnete Geschosse und
Trefferpartikel; höhere Stufen verstärken Spuren, Splitter, Stoßwellen und
Bühneneffekte. 280 Einträge sind einzeln kaufbar. Über die Shop-Pfeile sind
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

Die Grafik und Sounds werden zur Laufzeit ohne externe Assets erzeugt. Der
GitHub-Workflow nutzt nur einen Windows-Job, läuft nicht bei Pull-Requests
oder reinen README-Änderungen, vermeidet doppelte laufende Builds und lädt
nur das fertige `.exe` als Artifact hoch. Das hält die Actions-Kosten gering.
