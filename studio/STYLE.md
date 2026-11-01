# Stil-Bibel: „Absurde Straftat“-Videos (nach @outofthisworld_9), deutsche Version

## Formel (immer gleich)
1. **Normaler Einstieg**: „Dieser Mann hat …“ – alltägliche Handlung (Kühlschrank zu, Spiegel, Waage, surfen).
2. **Absurdes Ereignis** – wird *todernst* als Straftat benannt: „Das war **Einbruch**.“ / „Das war **Verleumdung**.“
3. **„Also rief er die Polizei.“** – kommt in jedem Video vor.
4. **Behörden machen logisch mit dem Unsinn weiter**: Verhör, Handschellen, Gericht, „Zehn Jahre Gefängnis.“
5. **Eskalation / Wendung**: oft mit „Währenddessen …“, neuer Täter, Rache, Gefängnis-Alltag.
6. **Trockene Pointe** – kurz, gern mit Kreis zum Anfang oder Umkehr („Sie hat einfach Angst.“).

## Text-Regeln
- Sätze 3–8 Wörter. Ein Satz = ein Shot = ein Untertitel.
- 12–16 Shots ≈ 30 s, oder 24–28 Shots ≈ 60 s.
- Zitate der Figuren in „…“, gern mit trockenem Fluch („Bist du dumm?“).
- Juristische Begriffe sind die Lacher: Hausfriedensbruch, Beamtenbeleidigung, Fahrerflucht, Ruhestörung, Diebstahl, versuchter Mord, Schwarzfahren, Steuerhinterziehung …
- Jeder Untertitel hat 1 hervorgehobenes Schlüsselwort (lachsrot).

## Look
- Low-Poly 3D, Pastellfarben, weiches Licht. Figuren: hoher eckiger Kopf mit gezeichnetem Gesicht (schwere Lider, Bartstoppeln).
- Hauptfigur meist im Anzug (rote Krawatte) oder Pyjama; Polizei blau-grau mit Mütze.
- Große dunkelblaue Schilder mit dem Delikt / Strafmaß („10 JAHRE“), Gefängniszelle mit Nummer.
- Kamera: langsame Fahrten, leichte Handkamera, viele Nahaufnahmen, POV-Inserts.

## Ton
- Stimme: de-DE-ConradNeural (+6 %, −2 Hz) – ruhig, emotionslos, Doku-Sprecher.
- Pause ~0,4 s nach jedem Satz. Leise Pizzicato-Musik, dezente Effekte (Boom bei Schildern, Sirene, Zellentür).

## Neues Video bauen
1. `videos/<slug>/story.py` anlegen (Vorlage: `videos/waage/story.py`): `SHOTS = [dict(text=..., hl=[...], scene=fn, sfx=[...])]`
2. Standbilder prüfen: `python3 make_video.py <slug> --still --preview` → `python3 tests/sheet.py <slug>`
3. Final: `python3 make_video.py <slug>` → `videos/<slug>/<slug>.mp4` (1080×1920, ~45 min Renderzeit)
