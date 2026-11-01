# TikTok-Video-Werkstatt

Wenn der Nutzer „erstell mir ein neues Video“ schreibt:
1. `bash studio/setup.sh` ausführen (installiert Blender-Modul, Stimme, Schriften).
2. `studio/STYLE.md` lesen – Formel, Look, Ton.
3. Neue Idee schreiben, `studio/videos/<slug>/story.py` nach Vorlage `studio/videos/waage/story.py` anlegen.
4. Standbilder prüfen: `cd studio && python3 make_video.py <slug> --still --preview && python3 tests/sheet.py <slug>`
5. Final rendern (~50 min, im Hintergrund): `python3 make_video.py <slug>` → MP4 an den Nutzer schicken.
Antworten auf Deutsch.
