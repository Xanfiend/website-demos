# Darba piezīmes

Publiskais portfolio un paraugu lapas, ko rāda GitHub Pages: https://xanfiend.github.io/website-demos/

## Uzbūve
- `index.html`: portfolio sākumlapa.
- `<nosaukums>/index.html`: ģenerētās paraugu lapas. Ar roku nelabot.
- Uzņēmumu saraksts nav šajā repozitorijā (`../privats/shops.py`). Uzņēmuma paraugs parādās tikai pēc pogas «Publicēt paraugu» privātajā sūtīšanas lapā; `python _src/build.py` atjauno tikai jau publicētos. `python _src/build.py --preview <saīsne>` uzbūvē paraugu privātajā mapē apskatei, to nepublicējot.
- `epasts.json`: e-pastu teksts (bez adresātiem). Mainot tekstu, palielināt `version`; privātā sūtīšanas lapa to ielādē ar pogu.
- `_src/autoserviss.html`: autoservisu veidne. `_src/build.py`: uzņēmumu saraksts un ģenerators. Pēc izmaiņām palaist `python3 _src/build.py`.
- `assets/`: attēli.

## Noteikumi
- Visi klientiem redzamie teksti ir latviski, vienkārši un godīgi: bez izdomātas statistikas, atsauksmēm vai klientu sarakstiem.
- Īstu uzņēmumu paraugiem jābūt skaidri apzīmētiem kā paraugiem (augšējā josla, piezīme īpašniekam, kājene, `noindex`), ar tālruņa, adreses un cenu piemēriem.
- E-pastus sūta tikai Raivo pats, tikai uz uzņēmumu adresēm, katrā ar atteikšanās rindu.
- Adresātu sarakstus un e-pasta adreses šeit neglabāt: repozitorijs ir publisks.
- Katrs uzņēmums saņem savu izskatu (`look()` failā `build.py`): izkārtojums, fonts, krāsas, stūru forma un foto tiek izvēlēti pēc uzņēmuma saīsnes un nemainās starp būvēšanas reizēm.
- Foto piemēri ir mapē `assets/foto/` (Unsplash licence, avoti failā `CREDITS.md`). Klienta lapā tos nomaina pret klienta foto.
- Jauns nozares veids: pievienot veidni mapē `_src/`, papildināt `build.py`, ielikt vispārīgo paraugu `index.html`.
