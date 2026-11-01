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
  Maustaste** treffen. **Sobald geschossen wird, stoppt die Uhr.** Lange
  Animationen (insbesondere der Raketen-Zielsucher) zählen nicht gegen dich.
  Danebenschießen, falsch treffen oder Zeitablauf kostet **genau ein Leben**.
  Du startest mit fünf Leben.
- Nach Fehlern wird die korrekte Antwort groß eingeblendet.
- Richtige Treffer bringen Münzen; schnellere Treffer und Serien mehr.
- **Jeder Run hat ein klares Ziel:** alle **28 unterschiedlichen Verben**
  mindestens einmal richtig beantworten. Richtige Antworten verlassen den
  Stapel; falsche Antworten und Zeitüberschreitungen kommen später erneut.
- Nach jeder Frage **außer der letzten erfolgreichen** öffnet der Shop.
  Er ist **nach Level 1 bis Level 10** sortiert und öffnet beim ersten Mal auf
  **Seite 1**. Danach merkt sich das Spiel die zuletzt besuchte Seite, auch
  nach dem Neustart. Über **ALLE LEVEL** und **GEKAUFT** kannst du jederzeit
  zwischen allen Upgrades und deiner bereits bezahlten Munition umschalten.
  Ein Klick auf gekaufte Munition rüstet sie **kostenlos erneut** aus. Die
  Auswahl bleibt gespeichert und hat Vorrang vor einem aktivierten Probeschuss.
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
Die einzelnen Levels sind keine identischen Farbvarianten: Jedes der 28
Geschosse erhält eine eigene Bewegung, Trefferinszenierung und ein Finale.
Die zehn Stufen bauen darauf auf: **Projektil, Leuchtspur, Begleitfunken, Spezialeffekt, Nebengeschoss, Orbits, Signatur-Welle, Nachhall, Bühnenlicht, Finale**.

Die **Rakete** steigt zuerst senkrecht mit Flamme und Rauch auf, kreist im
Suchflug, scannt mit ihrem Radar das angeklickte Ziel und fliegt nach dem Lock
als gelenkter Flugkörper hinein. Das dauert rund 2,3 Sekunden, aber die
Fragezeit steht nach dem Klick bereits still. Höhere Raketen-Levels zeigen
zusätzliche Begleitkörper, Zielmarkierungen und gestaffelte Explosionen.

Die 280 Einträge sind einzeln kaufbar. Der Shop zeigt in der Standardansicht
Level für Level. Alle gekauften Items bleiben über den Filter **GEKAUFT**
zugänglich und können ohne weitere Münzen wieder angelegt werden.

Die Fortschrittsdatei liegt unter
`%APPDATA%\IrregularRange\progress.json` (Windows) bzw.
`~/.local/share/irregular_range/progress.json` (Linux).

## Jede Munitionsart hat eine eigene Animation

| Munition | Start | Flug und Zielsuche | Treffer/Finale |
|---|---|---|---|
| Kreideblitz | Kreide bricht aus der Halterung | Zickzack-Schriftspur und Staub | Die Zielscheibe wird durchgestrichen |
| Konfettikanone | Papierkapsel platzt auf | Farbige Spirale aus Konfetti | Konfettiregen und zwei Zugaben |
| Tintenspritzer | Ein Tintenballon wird aufgezogen | Tropfender Tintenklecks fliegt im Bogen | Große Kleckse und kleine Spritzer |
| Gummiball | Flummi wird zusammengedrückt | Drei elastische Hüpfer | Prallender Ball und Gummiring |
| Laser | Ladeglühen am Laser | Präziser dünner Lichtstrahl | Kreuzförmiger Neonblitz |
| Sternenstaub | Ein Stern beginnt zu funkeln | Sternschnuppe mit Satelliten | Sternennebel und funkelnde Spitzen |
| Papierflieger | Papierflieger faltet seine Flügel | Gleitflug mit Rückenwind | Mini-Flieger ziehen Kreise |
| Feuerwerk | Zündschnur glimmt | Feuerwerksrakete steigt auf | Mehrstufige bunte Feuerwerksblüten |
| Explosion | Cartoon-Bombe zündet | Schwere Kugel mit Rauchfahne | KABOOM-Stoßwellen und Splitter |
| Fußball | Anstoß an der Torlinie | Rotierender Fußball im hohen Bogen | Tor-Netz wackelt und Bälle fliegen |
| Gewitter | Elektrostatik sammelt sich | Blitz springt in Zickzacks | Verzweigte, pulsierende Blitze |
| Schneesturm | Eisnebel formt eine Schneeflocke | Langsam schwebender Schneewirbel | Wirbelsturm aus Schneekristallen |
| Wasserschlacht | Wasserballon füllt sich | Schwungvoller Bogen mit Tropfen | Schwall, Wasserfontänen und Tropfen |
| Seifenblasen | Seifenblase wird aufgepustet | Leichte Blasen steigen schwankend | Blasenplatzer mit schimmernden Ringen |
| Meteoriten | Feuriger Stein stürzt vom Himmel | Glühender Schweif mit Funken | Meteoritenkrater mit Trümmerregen |
| Kristallregen | Kristall lädt seinen Facettenglanz | Rotierender Diamant mit Prismenspuren | Splitterfächer aus farbigen Kristallen |
| Herzchenhagel | Herz beginnt zu schlagen | Flatternde Herzen schweben | Herzregen und pulsierende Konturen |
| Donutwerfer | Donut wird in Rotation versetzt | Zuckerglasur wirbelt durch die Luft | Streusel-Konfetti und Donut-Ringe |
| Pizzaschleuder | Pizzascheibe hebt ab | Rotierendes Pizzastück im Wurfbogen | Käseschnüre und Peperonikonfetti |
| Raketenstart | Rakete startet senkrecht mit Triebwerk | Radar sucht, erfasst und verfolgt das angeklickte Ziel | Raketeneinschlag mit Rauch und gestaffelten Explosionen |
| Kometenschweif | Ein Komet entzündet sich | Heller Kern mit langem Schweif | Gleißende Kometenstücke zerfallen |
| Regenbogen | Prismastrahl öffnet sich | Bunter Regenbogen spannt sich | Siebenfarbige Wellen am Ziel |
| Farbexplosion | Farbpatrone wird abgeschossen | Tropfen ziehen Spritzspuren | Verschiedene Farbflecken bedecken das Ziel |
| Discokugel | Discokugel wird beleuchtet | Fliegender Spiegelball mit Lichtkegeln | Tanzende Lichtstrahlen und Farbblitze |
| Plasmapuls | Plasmafeld lädt sich auf | Pulsierendes Plasmageschoss | Konzentrierte Energieringe und Funken |
| Ninja-Stern | Wurfstern schnappt aus der Hand | Schnell rotierender Shuriken in Zickzacks | Viele kleine Wurfsterne fliegen auseinander |
| Galaxienwirbel | Ein Sternennebel kondensiert | Umlaufende Sterne spiralen zum Ziel | Galaktischer Wirbel mit Sternensturm |
| Goldregen | Eine Münze wird hochgeschnippt | Überschlagender Münzregen | Goldene Jackpot-Fontäne |

Die Flug- und Level-Inszenierungen werden durch `weapon_fx.py` und
`weapon_choreography.py` gesteuert, die eigenen Einschläge durch
`weapon_visuals.py`. Alle Animationen benutzen Pygame-Primitiven.

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
python scripts/fetch_fonts.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --add-data "assets/fonts;assets/fonts" --name IrregularRange game.py
```

Effekte und Sounds werden mit Pygame zur Laufzeit erzeugt. Drei freie
Google-Schriftarten werden beim Windows-Build eingebettet. Die Tests prüfen
den endlichen Run, die angehaltene Stoppuhr, gespeicherte Shop-Seiten,
gekaufte Waffen, einmalige Bonusauszahlung und alle 28 Inszenierungen. Der GitHub-Workflow testet
zusätzlich ein paar Spielbilder ohne sichtbares Fenster. Er nutzt nur einen Windows-Job, läuft nicht bei Pull-Requests
oder reinen README-Änderungen, vermeidet doppelte laufende Builds und lädt
die `.exe` und kurze UI-Vorschaubilder als getrennte Artifacts hoch.
Jeder relevante Push startet nur **einen Windows-Job**; reine Dokumentations-
änderungen lösen keinen erneuten Windows-Build aus.


## Grafikdesign und Schriftarten

Das dunkelblaue Neon-Layout orientiert sich an den Referenz-Screenshots:
Hintergrund `#060914`, Panels `#121A36`, Cyan `#22E6FF`,
Treffer-Lime `#B6FF3B`, Gold `#FFC53D`, Combo-Orange `#FF7A1A`.
Die Fluganimationen werden auf den Schießbereich begrenzt, damit sie weder
Verb und Antworttexte noch HUD/Shop verdecken.

Die drei Schriften **Russo One**, **Chakra Petch** und **Orbitron** werden bei
GitHub Actions aus dem offiziellen Google-Fonts-Repository heruntergeladen und
mit den SIL-OFL-Lizenzen in die Windows-EXE eingebettet. Es muss nichts
nachinstalliert werden. Ohne diese Dateien werden gut lesbare
Systemschriftarten als Fallback verwendet.
