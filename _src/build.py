"""Builds demo pages from _src/autoserviss.html.

  python3 _src/build.py          rebuild the generic demos and every business demo already published
  python3 _src/build.py <slug>   create or update one business demo (used by the publish button)
  python3 _src/build.py --preview <slug> ...   build business demos into privats/preview/ to look at them unpublished

Business data lives in the private privats/shops.py (never committed)."""
import html, json, pathlib, re, runpy, shutil, sys, urllib.parse, zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = (ROOT / "_src" / "autoserviss.html").read_text(encoding="utf-8")

# slug, name, "in <town>" (locative), town, services, what customers type into Google
SHOPS = [
    ("autoserviss", "Jūsu Autoserviss", "", "Jūsu pilsēta",
     ["Diagnostika", "Apkope", "Ritošās daļas remonts", "Riepu serviss"], ""),
    ("ziedu-salons", "Jūsu Ziedu Salons", "", "Jūsu pilsēta",
     ["Pušķi un kompozīcijas", "Kāzu floristika", "Sēru vainagi", "Telpaugi", "Ziedu piegāde"], "", "ziedi"),
    ("kafejnica", "Jūsu Kafejnīca", "", "Jūsu pilsēta",
     ["Dienas pusdienas", "Banketi un svinības", "Izbraukuma banketi", "Bēru mielasti", "Kūkas un konditoreja"], "", "kafe"),
    ("zobarstnieciba", "Jūsu Zobārstniecība", "", "Jūsu pilsēta",
     ["Zobu ārstēšana", "Zobu higiēna", "Protezēšana", "Zobu balināšana", "Bērnu zobārstniecība"], "", "zobi"),
    ("apbedisanas-birojs", "Jūsu Apbedīšanas Birojs", "", "Jūsu pilsēta",
     ["Bēru organizēšana", "Zārki un piederumi", "Transports", "Sēru vainagi", "Palīdzība ar dokumentiem"], "", "beres"),
    ("frizetava", "Jūsu Frizētava", "", "Jūsu pilsēta",
     ["Sieviešu griezumi", "Vīriešu griezumi", "Matu krāsošana", "Svētku frizūras", "Manikīrs"], "", "friz"),
    ("veterinara-klinika", "Jūsu Veterinārā Klīnika", "", "Jūsu pilsēta",
     ["Vakcinācija un čipēšana", "Terapija", "Ķirurģija", "Zobu kopšana", "Veterinārā aptieka"], "", "vet"),
    ("buvfirma", "Jūsu Būvfirma", "", "Jūsu pilsēta",
     ["Remontdarbi", "Jumtu darbi", "Flīzēšana un apdare", "Ūdensapgāde un kanalizācija"], "", "buve"),
]
GENERIC = {s[0] for s in SHOPS}
# private folder: inside the repo folder (git-excluded) or next to it
PRIV = ROOT / "privats" if (ROOT / "privats").is_dir() else ROOT.parent / "privats"
_PRIVATE = PRIV / "shops.py"
if _PRIVATE.exists():
    SHOPS += runpy.run_path(str(_PRIVATE))["SHOPS"]
# public address, phone, hours and map position from zl.lv (privats/fetch_info.py)
_INFO = PRIV / "info.json"
INFO = json.loads(_INFO.read_text(encoding="utf-8")) if _INFO.exists() else {}
_FLAGS = PRIV / "contacts.json"  # only the "card" tick is read here
HAS_CARD = {k for k, v in json.loads(_FLAGS.read_text(encoding="utf-8")).items() if v.get("card")} if _FLAGS.exists() else set()
DAYNAMES = {1: "Pirmdiena", 2: "Otrdiena", 3: "Trešdiena", 4: "Ceturtdiena", 5: "Piektdiena", 6: "Sestdiena", 0: "Svētdiena"}


def nice_tel(t):
    d = re.sub(r"\D", "", t)
    d = d[3:] if d.startswith("371") and len(d) == 11 else d
    return f"+371 {d[:2]} {d[2:5]} {d[5:]}" if len(d) == 8 else t


def hours_html(h):
    """Group consecutive days with the same hours: Pirmdiena–piektdiena 8.00–17.00."""
    rows, order = [], [1, 2, 3, 4, 5, 6, 0]
    val = {d: re.sub(r"(^|–)0(\d)", r"\1\2", h[str(d)]) if str(d) in h else "Slēgts" for d in order}
    for d in order:
        if rows and rows[-1][2] == val[d]:
            rows[-1][1] = d
        else:
            rows.append([d, d, val[d]])
    out = []
    for a, b, v in rows:
        days = "".join(str(x) for x in order[order.index(a):order.index(b) + 1])
        label = DAYNAMES[a] if a == b else f"{DAYNAMES[a]}–{DAYNAMES[b].lower()}"
        out.append(f'        <div data-d="{days}"><span>{label}</span><span>{v}</span></div>')
    return "\n".join(out)


def real_info(page, info, ld):
    """Put the business's public details into the page instead of placeholders."""
    tel = info.get("tel")
    if tel:
        nt, href = nice_tel(tel), "tel:" + re.sub(r"[^\d+]", "", tel)
        page = page.replace('<span class="phone"><svg class="i"><use href="#phone"/></svg><span>Jūsu tālrunis</span></span>',
                            f'<a class="phone" href="{href}"><svg class="i"><use href="#phone"/></svg><span>{nt}</span></a>')
        page = page.replace("<small>Tālrunis</small>Jūsu tālrunis", f'<small>Tālrunis</small><a href="{href}">{nt}</a>')
        page = page.replace('<a class="btn ghost" href="#pieteikums"><svg class="i"><use href="#phone"/></svg>Zvanīt</a>',
                            f'<a class="btn ghost" href="{href}"><svg class="i"><use href="#phone"/></svg>Zvanīt</a>')
        ld["telephone"] = "+" + re.sub(r"\D", "", tel).lstrip("+") if not tel.startswith("+") else tel
    if info.get("addr"):
        shown = re.sub(r"\s*\([^)]*\)", "", info["addr"])  # the catalogue adds English directions in brackets
        page = re.sub(r"<small>Adrese</small>Jūsu adrese, [^<]*", lambda m: "<small>Adrese</small>" + html.escape(shown), page)
        ld["address"]["streetAddress"] = info["addr"]
    if info.get("hours"):
        page = re.sub(r'(<div class="hours" id="hours">\n).*?(\n      </div>)', lambda m: m.group(1) + hours_html(info["hours"]) + m.group(2), page, count=1, flags=re.S)
    q = ",".join(map(str, info["geo"])) if info.get("geo") else info.get("addr", "")
    if q:
        url = "https://www.google.com/maps/search/?api=1&amp;query=" + urllib.parse.quote(q)
        attr = btn = ""
        if info.get("geo"):  # the sample loads the map when scrolled to; the client site only on a click (see make_live)
            la, lo = info["geo"]
            attr = (f' data-auto data-src="https://www.openstreetmap.org/export/embed.html?bbox={lo - .011:.5f}%2C{la - .0055:.5f}%2C{lo + .011:.5f}%2C{la + .0055:.5f}'
                    f'&amp;layer=mapnik&amp;marker={la:.5f}%2C{lo:.5f}"')
            btn = '<button type="button" class="btn ghost">Rādīt karti</button>'
        page = re.sub(r'<div class="map">.*?</div>', lambda m: f'<div class="map"{attr}>{btn}<a href="{url}" target="_blank" rel="noopener"><svg class="i"><use href="#pin"/></svg>Atvērt Google kartē</a></div>', page, count=1, flags=re.S)
        if info.get("geo"):
            ld["geo"] = {"@type": "GeoCoordinates", "latitude": info["geo"][0], "longitude": info["geo"][1]}
    page = page.replace("Teksti, cenas, tālrunis un adrese ir piemēri, tos nomainīšu pret jūsējiem.",
                        "Adrese, tālrunis un darba laiks ir no publiskā uzņēmumu kataloga. Teksti un cenas ir piemēri, tos nomainīšu pret jūsējiem.")
    page = page.replace("Tā nav uzņēmuma oficiālā mājaslapa, un teksti, cenas un kontakti ir piemēri.",
                        "Tā nav uzņēmuma oficiālā mājaslapa. Kontakti ir no publiskā uzņēmumu kataloga, teksti un cenas ir piemēri.")
    return page


def self_host_fonts(page, out):
    """Download the Google Fonts the page uses into fonts/ so visitors' browsers never contact Google (GDPR)."""
    import urllib.request
    cache = PRIV / "fonts-cache"
    cache.mkdir(exist_ok=True)
    (out / "fonts").mkdir(exist_ok=True)
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
    css_all = []
    for href in re.findall(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', page):
        css = urllib.request.urlopen(urllib.request.Request(html.unescape(href), headers=ua), timeout=30).read().decode()
        for u in re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css):
            fn = re.sub(r"[^\w.]+", "_", u.split("/s/", 1)[-1])
            f = cache / fn
            if not f.exists():
                f.write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=ua), timeout=30).read())
            (out / "fonts" / fn).write_bytes(f.read_bytes())
            css = css.replace(u, "fonts/" + fn)
        css_all.append(css)
    page = re.sub(r'<link rel="preconnect" href="https://fonts\.g[^"]+"( crossorigin)?>\n', "", page)
    page = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]+">\n?', "", page)
    return page.replace("<style>", "<style>\n" + "\n".join(css_all), 1)


PRIVACY = """<!doctype html>
<html lang="lv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privātuma politika · {name}</title><meta name="robots" content="noindex">
<style>body{{font:17px/1.6 system-ui,sans-serif;max-width:720px;margin:0 auto;padding:32px 20px;color:#14262b;background:#fff}}h1{{font-size:1.8rem}}h2{{font-size:1.15rem;margin-top:28px}}a{{color:inherit}}
@media (prefers-color-scheme:dark){{body{{background:#0f1a1d;color:#e9efee}}}}</style></head><body>
<p><a href="./">← {name}</a></p>
<h1>Privātuma politika</h1>
<p>Spēkā no {date}.</p>
<h2>Kas apstrādā datus</h2>
<p>{company}{regnr}. Saziņai par datiem: {email}.</p>
<h2>Kādus datus vācam un kāpēc</h2>
<p>Ja aizpildāt pieteikuma formu, saņemam jūsu vārdu, tālruni un ziņu. Tos izmantojam tikai, lai atbildētu uz jūsu pieteikumu un vienotos par pakalpojumu. Juridiskais pamats: pasākumi pēc jūsu pieprasījuma pirms līguma noslēgšanas (VDAR 6. panta 1. punkta b) apakšpunkts).</p>
<h2>Kas vēl redz datus</h2>
<p>Pieteikumu mums piegādā e-pasta piegādes pakalpojums Web3Forms, kas datus apstrādā tikai piegādes nolūkā. Datus nepārdodam un nenododam citiem.</p>
<h2>Cik ilgi glabājam</h2>
<p>Tik ilgi, cik vajadzīgs, lai atbildētu uz pieteikumu un sniegtu pakalpojumu, bet ne ilgāk par vienu gadu, ja vien likums neprasa ilgāk (piemēram, grāmatvedības dokumentiem).</p>
<h2>Sīkdatnes</h2>
<p>Šī lapa neizmanto sīkdatnes un neseko apmeklētājiem. Fonti tiek ielādēti no šīs pašas lapas.{maps}</p>
<h2>Jūsu tiesības</h2>
<p>Jūs varat lūgt piekļuvi saviem datiem, to labošanu vai dzēšanu, kā arī iebilst pret apstrādi, rakstot uz {email}. Ja uzskatāt, ka dati apstrādāti nepareizi, varat vērsties Datu valsts inspekcijā (www.dvi.gov.lv).</p>
</body></html>
"""

LIVE_JS = """document.getElementById('req').addEventListener('submit', function (e) {
  e.preventDefault();
  var f = e.target, b = f.querySelector('button[type=submit]'), s = document.getElementById('sent');
  b.disabled = true;
  fetch('https://api.web3forms.com/submit', { method: 'POST', body: new FormData(f) })
    .then(function (r) { return r.json(); })
    .then(function (d) { if (!d.success) throw 0; f.reset(); s.textContent = 'Paldies! Pieteikums ir nosūtīts, drīz sazināsimies.'; })
    .catch(function () { s.textContent = 'Neizdevās nosūtīt. Lūdzu, piezvaniet mums.'; })
    .finally(function () { s.hidden = false; b.disabled = false; });
});"""


def make_live(page, name, cfg, out):
    """Turn a demo into the client's real site: no sample markings, working form, privacy page, own domain."""
    import datetime
    assert cfg.get("form_key") and cfg.get("email"), f"add form_key and email for this business to privats/live.json"
    e = html.escape
    page = re.sub(r'<div class="demo-note">.*?</div></div>\n', "", page, count=1, flags=re.S)
    page = re.sub(r'<section class="owner">.*?</section>\n', "", page, count=1, flags=re.S)
    page = page.replace(" · mājaslapas paraugs</title>", "</title>").replace('<meta name="robots" content="noindex">\n', "")
    page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(name)}: pakalpojumi, cenas, darba laiks un kontakti.">', page)
    if cfg.get("domain"):
        page = page.replace("</title>", f'</title>\n<link rel="canonical" href="https://{cfg["domain"]}/">', 1)
    page = re.sub(r"(<footer>.*?<p>).*?(</p>)", lambda m: m.group(1) + f'© {datetime.date.today().year} {e(name)} · <a href="privatums.html">Privātuma politika</a>' + m.group(2), page, count=1, flags=re.S)
    page = page.replace('<form id="req" class="rv">', '<form id="req" class="rv">\n      <input type="hidden" name="access_key" value="%s">\n'
                        '      <input type="hidden" name="subject" value="Jauns pieteikums no mājaslapas">\n'
                        '      <input type="checkbox" name="botcheck" hidden tabindex="-1" autocomplete="off">' % e(cfg["form_key"]))
    page = page.replace('<p id="sent" hidden>', '<p class="fine">Datus izmantojam tikai, lai atbildētu uz pieteikumu. <a href="privatums.html">Privātuma politika</a></p>\n      <p id="sent" hidden>')
    page = re.sub(r"document\.getElementById\('req'\)\.addEventListener\('submit'.*?\n\}\);", lambda m: LIVE_JS, page, count=1, flags=re.S)
    page = page.replace('<div class="map" data-auto ', '<div class="map" ')
    for fn in set(re.findall(r'\.\./assets/foto/([\w-]+\.jpg)', page)):
        (out / "foto").mkdir(exist_ok=True)
        shutil.copy(ROOT / "assets" / "foto" / fn, out / "foto" / fn)
    page = page.replace("../assets/foto/", "foto/")
    page = self_host_fonts(page, out)
    files = {"privatums.html": PRIVACY.format(maps=" Karte tiek ielādēta no OpenStreetMap tikai tad, ja nospiežat «Rādīt karti»." if 'class="map" data-src' in page else "",
                                              name=e(name), date=datetime.date.today().strftime("%d.%m.%Y"),
                                              company=e(cfg.get("company", name)), regnr=f", reģ. nr. {e(cfg['regnr'])}" if cfg.get("regnr") else "",
                                              email=e(cfg["email"]))}
    if cfg.get("domain"):
        files["CNAME"] = cfg["domain"] + "\n"
        files["robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: https://{cfg['domain']}/sitemap.xml\n"
        files["sitemap.xml"] = (f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                f'  <url><loc>https://{cfg["domain"]}/</loc></url>\n</urlset>\n')
    return page, files
WANT = {a for a in sys.argv[1:] if not a.startswith("--")}
PREVIEW = "--preview" in sys.argv  # privats/preview/<slug>/, nothing is published
LIVE = "--live" in sys.argv  # build the client's real site into ../klienti/<slug>/ (see privats/go-live.html)
_LIVECFG = PRIV / "live.json"
LIVECFG = json.loads(_LIVECFG.read_text(encoding="utf-8-sig")) if _LIVECFG.exists() else {}
assert not LIVE or WANT, "--live needs a business slug"
_unknown = WANT - {s[0] for s in SHOPS}
assert not _unknown, f"unknown slug: {_unknown}"


def wanted(slug):
    if WANT:
        return slug in WANT
    return slug in GENERIC or (ROOT / slug / "index.html").exists()


WINTER = ("Ziemas riepas obligātas no 1. decembra", "Riepu maiņa bez rindas, piesakoties iepriekš.")
GENERIC_SUB = "Cenu piemēri. Precīzu cenu jūsu auto nosaucam pirms darba."
# profile: page copy that changes with the kind of shop. Prices are placeholders the owner replaces.
# noun, h1, lead, estimate rows (last = total), season banner, price intro, price rows (name, note, price)
PROFILES = {
    "auto": ("Autoserviss", "Remonts bez <em>pārsteigumiem</em> rēķinā",
        "Pirms sākam darbu, jūs saņemat tāmi ar cenu. Ja remonta laikā atklājas vēl kas, vispirms piezvanām un tikai tad darām.",
        [("Priekšējo bremžu kluču maiņa", "35,00"), ("Bremžu kluči, komplekts", "42,00"), ("Bremžu sistēmas pārbaude", "0,00"), ("Kopā ar PVN", "77,00")],
        WINTER, "Darba cenas vieglajām automašīnām. Detaļas rēķinām atsevišķi un nosaucam cenu pirms pasūtīšanas.",
        [("Eļļas un filtra maiņa", "Eļļu varat atvest arī savu", "no 25 €"), ("Riepu maiņa, 4 riteņi", "Ar balansēšanu", "no 30 €"),
         ("Bremžu kluču maiņa, viena ass", "", "no 35 €"), ("Datordiagnostika", "Kļūdu nolasīšana un skaidrojums", "no 20 €"),
         ("Ritošās daļas pārbaude", "", "no 15 €"), ("Sagatavošana tehniskajai apskatei", "Pārbaudām to pašu, ko skatīs apskatē", "no 25 €"),
         ("Kondicioniera uzpilde", "", "no 45 €")]),
    "kravas": ("Kravas auto serviss", "Kravas auto atpakaļ uz ceļa <em>bez liekas dīkstāves</em>",
        "Katra stāvēšanas diena maksā. Pirms darba nosaucam cenu un termiņu, un paziņojam uzreiz, ja kas mainās.",
        [("Bremžu uzliku maiņa, viena ass", "90,00"), ("Bremžu uzlikas, komplekts", "140,00"), ("Bremžu sistēmas pārbaude", "0,00"), ("Kopā bez PVN", "230,00")],
        None, "Darba cenu piemēri kravas transportam. Detaļas rēķinām atsevišķi un nosaucam cenu pirms pasūtīšanas.",
        [("Datordiagnostika", "Kļūdu nolasīšana un skaidrojums", "no 40 €"), ("Eļļas un filtru maiņa", "", "no 80 €"),
         ("Bremžu uzliku maiņa, viena ass", "", "no 90 €"), ("Riepas maiņa, viens ritenis", "", "no 15 €"),
         ("Sagatavošana tehniskajai apskatei", "", "no 50 €"), ("Metināšanas darbi", "Pēc apskates", "pēc tāmes")]),
    "evak": ("Evakuators", "Evakuators, kad auto <em>vairs nebrauc</em>",
        "Piezvaniet, un uzreiz pateiksim cenu un pēc cik ilga laika būsim klāt. Aizvedam uz servisu vai mājām.",
        [("Izsaukums pilsētā", "40,00"), ("Ceļš ārpus pilsētas, 20 km", "20,00"), ("Iekraušana un nostiprināšana", "0,00"), ("Kopā ar PVN", "60,00")],
        None, "Cenu piemēri. Precīzu cenu nosaucam pa telefonu, pirms izbraucam.",
        [("Evakuācija pilsētā", "", "no 40 €"), ("Evakuācija ārpus pilsētas", "Par katru kilometru", "no 1 €/km"),
         ("Akumulatora palaišana", "", "no 20 €"), ("Riepas maiņa uz ceļa", "", "no 20 €"),
         ("Izvilkšana no grāvja", "Atkarīgs no vietas", "pēc vienošanās")]),
    "riepas": ("Riepu serviss", "Riepu maiņa <em>bez rindas</em>",
        "Piesakieties uz konkrētu laiku, un jums nav jāgaida. Cenu zināt jau pirms ierašanās.",
        [("Riepu maiņa, 4 riteņi", "24,00"), ("Balansēšana, 4 riteņi", "16,00"), ("Riepu spiediena pārbaude", "0,00"), ("Kopā ar PVN", "40,00")],
        WINTER, "Cenu piemēri vieglajām automašīnām. Citai tehnikai cenu nosaucam pa telefonu.",
        [("Riepu maiņa ar balansēšanu, R13–R15", "4 riteņi", "no 30 €"), ("Riepu maiņa ar balansēšanu, R16–R18", "4 riteņi", "no 40 €"),
         ("Riepas remonts", "", "no 10 €"), ("Sezonas riepu glabāšana", "4 riepas, viena sezona", "no 25 €"),
         ("Kravas auto riepas montāža", "Viens ritenis", "no 20 €")]),
    "virsbuve": ("Virsbūves remonts un krāsošana", "Virsbūve <em>kā no jauna</em>",
        "Atsūtiet bojājuma foto un saņemiet tāmi. Pirms darba zināt cenu un termiņu.",
        [("Bampera remonts", "60,00"), ("Bampera krāsošana", "120,00"), ("Krāsas toņa piemeklēšana", "0,00"), ("Kopā ar PVN", "180,00")],
        None, GENERIC_SUB,
        [("Vienas detaļas krāsošana", "", "no 120 €"), ("Bampera remonts", "", "no 60 €"), ("Skrāpējumu pulēšana", "", "no 30 €"),
         ("Virsbūves pulēšana", "", "no 90 €"), ("Lukturu pulēšana", "Abi lukturi", "no 25 €")]),
    "stikli": ("Auto stikli", "Stikla maiņa ar <em>skaidru cenu</em>",
        "Nosauciet auto marku un gadu, un pateiksim cenu un laiku. Mazas plaisas bieži var salabot, nemainot stiklu.",
        [("Vējstikls", "110,00"), ("Stikla ielīmēšana", "50,00"), ("Vecā stikla utilizācija", "0,00"), ("Kopā ar PVN", "160,00")],
        None, GENERIC_SUB,
        [("Vējstikla maiņa", "Ar stiklu un darbu", "no 150 €"), ("Sānu stikla maiņa", "", "no 60 €"), ("Aizmugurējā stikla maiņa", "", "no 120 €"),
         ("Plaisas remonts", "", "no 25 €"), ("Stikli kravas auto un traktoriem", "", "pēc pieprasījuma")]),
    "gaze": ("Auto gāzes iekārtas", "Brauciet lētāk <em>ar gāzi</em>",
        "Uzstādām un remontējam auto gāzes iekārtas. Pirms darba nosaucam pilnu cenu: iekārta, uzstādīšana un regulēšana.",
        [("Gāzes iekārta, 4 cilindri", "420,00"), ("Uzstādīšana un regulēšana", "180,00"), ("Pārbaude pēc 1000 km", "0,00"), ("Kopā ar PVN", "600,00")],
        None, GENERIC_SUB,
        [("Gāzes iekārtas uzstādīšana", "Ar iekārtu un regulēšanu", "no 600 €"), ("Iekārtas apkope un filtru maiņa", "", "no 30 €"),
         ("Regulēšana", "", "no 25 €"), ("Datordiagnostika", "Benzīna un gāzes dzinējiem", "no 20 €"), ("Sprauslu tīrīšana", "", "no 40 €")]),
    "karbas": ("Ātrumkārbu remonts", "Ātrumkārbu remonts ar <em>skaidru tāmi</em>",
        "Vispirms diagnostika, tad tāme. Remontējam automātiskās un mehāniskās ātrumkārbas un godīgi pasakām, vai remonts atmaksājas.",
        [("Ātrumkārbas diagnostika", "40,00"), ("Eļļas un filtra maiņa automātam", "90,00"), ("Izmēģinājuma brauciens", "0,00"), ("Kopā ar PVN", "130,00")],
        None, GENERIC_SUB,
        [("Ātrumkārbas diagnostika", "", "no 40 €"), ("Eļļas maiņa automātiskajā ātrumkārbā", "", "no 90 €"), ("Sajūga maiņa", "", "no 150 €"),
         ("Ātrumkārbas remonts", "Pēc diagnostikas", "pēc tāmes"), ("Ritošās daļas pārbaude", "", "no 15 €")]),
    "sture": ("Stūres iekārtu remonts", "Stūres reikas remonts <em>bez minēšanas</em>",
        "Atrodam vainu, nosaucam cenu un tikai tad remontējam. Turpat veicam arī ikdienas apkopi.",
        [("Stūres reikas diagnostika", "20,00"), ("Stūres reikas restaurācija", "180,00"), ("Savirzes pārbaude pēc remonta", "0,00"), ("Kopā ar PVN", "200,00")],
        None, GENERIC_SUB,
        [("Stūres reikas restaurācija", "", "no 180 €"), ("Elektriskās stūres remonts", "Pēc diagnostikas", "pēc tāmes"),
         ("Savirzes regulēšana", "", "no 30 €"), ("Eļļas un filtra maiņa", "", "no 25 €"), ("Bremžu kluču maiņa, viena ass", "", "no 35 €"),
         ("Riepu maiņa, 4 riteņi", "Ar balansēšanu", "no 30 €")]),
    "dizelis": ("Dīzeļa sistēmu remonts", "Sprauslu remonts, kad zināt, <em>par ko maksājat</em>",
        "Pārbaudām sprauslas un sūkņus un parādām rezultātu. Remontējam tikai to, kas tiešām jāremontē.",
        [("Sprauslu pārbaude, 4 gab.", "40,00"), ("Vienas sprauslas remonts", "90,00"), ("Pārbaudes rezultātu izdruka", "0,00"), ("Kopā ar PVN", "130,00")],
        None, GENERIC_SUB,
        [("Sprauslas pārbaude", "Viena sprausla", "no 10 €"), ("Sprauslas remonts", "", "no 90 €"), ("Augstspiediena sūkņa diagnostika", "", "no 40 €"),
         ("Dīzeļa sistēmas datordiagnostika", "", "no 25 €"), ("Sūkņa remonts", "Pēc diagnostikas", "pēc tāmes")]),
    "prets": ("Pretrūsas apstrāde un autoserviss", "Pasargājiet auto <em>no rūsas</em>",
        "Apstrādājam auto apakšu un slēptās vietas. Pirms darba parādām, kādā stāvoklī ir virsbūve, un nosaucam cenu.",
        [("Apakšas mazgāšana un žāvēšana", "40,00"), ("Pretrūsas apstrāde, apakša", "180,00"), ("Foto pirms un pēc", "0,00"), ("Kopā ar PVN", "220,00")],
        ("Sāls uz ceļiem bojā virsbūvi", "Pretrūsas apstrādi vislabāk veikt pirms ziemas."), GENERIC_SUB,
        [("Pretrūsas apstrāde, vieglais auto", "", "no 220 €"), ("Pretrūsas apstrāde, apvidus auto vai mikroautobuss", "", "no 280 €"),
         ("Bremžu kluču maiņa, viena ass", "", "no 35 €"), ("Datordiagnostika", "", "no 20 €"), ("Sagatavošana tehniskajai apskatei", "", "no 25 €")]),
    "ziedi": ("Ziedu salons", "Svaigi ziedi <em>katram gadījumam</em>",
        "Pušķi, kompozīcijas un telpaugi. Pasūtiet iepriekš, un pušķis būs gatavs, kad atnāksiet.",
        [("Pušķis no sezonas ziediem", "25,00"), ("Apsveikuma kartīte", "2,00"), ("Iesaiņošana", "0,00"), ("Kopā", "27,00")],
        ("Ziemassvētku vainagi un kompozīcijas", "Pasūtījumus pieņemam jau tagad."),
        "Cenu piemēri. Pušķi veidojam arī konkrētai summai, nosauciet savu budžetu.",
        [("Pušķis no sezonas ziediem", "", "no 15 €"), ("Rozes", "Viens zieds", "no 2,50 €"), ("Līgavas pušķis", "", "no 45 €"),
         ("Galda kompozīcija", "", "no 20 €"), ("Sēru vainags", "", "no 40 €"), ("Telpaugs podiņā", "", "no 8 €")]),
    "kafe": ("Kafejnīca", "Gardas pusdienas un <em>svētku galdi</em>",
        "Siltas pusdienas katru darba dienu un banketi jūsu svētkiem. Ēdienkarti un cenas redzat jau iepriekš.",
        [("Dienas zupa", "2,50"), ("Otrais ēdiens ar piedevām", "5,50"), ("Deserts", "2,00"), ("Komplekts kopā", "10,00")],
        ("Gada nogales pasākumi", "Brīvie datumi aizpildās ātri, piesakieties laikus."),
        "Cenu piemēri. Banketa piedāvājumu sagatavojam pēc viesu skaita un jūsu vēlmēm.",
        [("Dienas pusdienu komplekts", "Zupa un otrais ēdiens", "no 6 €"), ("Zupa", "", "no 2,50 €"), ("Otrais ēdiens", "", "no 5 €"),
         ("Banketa galds", "Vienai personai", "no 25 €"), ("Bēru mielasts", "Vienai personai", "no 15 €"),
         ("Izbraukuma banketi", "", "pēc piedāvājuma")]),
    "zobi": ("Zobārstniecība", "Zobārstniecība ar <em>skaidrām cenām</em>",
        "Pirms ārstēšanas saņemat plānu un izmaksas. Pieteikties var arī vakarā, kad reģistratūra ir slēgta.",
        [("Konsultācija un apskate", "25,00"), ("Zoba plombēšana", "55,00"), ("Rentgena uzņēmums", "10,00"), ("Kopā", "90,00")],
        None, "Cenu piemēri. Precīzas izmaksas nosaucam pēc apskates, pirms ārstēšanas.",
        [("Konsultācija un apskate", "", "no 25 €"), ("Zobu higiēna", "", "no 50 €"), ("Plomba", "", "no 45 €"),
         ("Zoba izraušana", "", "no 40 €"), ("Rentgena uzņēmums", "", "no 10 €"), ("Zobu balināšana", "", "no 150 €")]),
    "beres": ("Apbedīšanas pakalpojumi", "Palīdzam <em>grūtā brīdī</em>",
        "Uzņemamies bēru organizēšanas darbus, lai jums par tiem nebūtu jādomā. Piezvaniet, un pastāstīsim, kas jādara vispirms.",
        [("Zārks ar aprīkojumu", "280,00"), ("Transports", "60,00"), ("Palīdzība ar dokumentiem", "0,00"), ("Kopā", "340,00")],
        None, "Cenu piemēri. Pilnas izmaksas nosaucam sarunā, atbilstoši jūsu vēlmēm.",
        [("Zārki", "", "no 150 €"), ("Transports pilsētā", "", "no 40 €"), ("Kapa rakšana un aizbēršana", "", "no 120 €"),
         ("Sēru vainagi", "", "no 35 €"), ("Kremācijas organizēšana", "", "pēc pieprasījuma")]),
    "friz": ("Frizētava", "Jauna frizūra <em>bez gaidīšanas rindā</em>",
        "Piesakieties sev ērtā laikā, arī vakarā. Cenas redzat iepriekš.",
        [("Sieviešu matu griezums", "25,00"), ("Matu krāsošana", "45,00"), ("Konsultācija", "0,00"), ("Kopā", "70,00")],
        ("Svētku frizūras", "Decembra laiki aizpildās ātri, piesakieties laikus."),
        "Cenu piemēri. Precīzu cenu nosaucam pēc matu garuma un darba apjoma.",
        [("Sieviešu griezums", "", "no 20 €"), ("Vīriešu griezums", "", "no 12 €"), ("Bērnu griezums", "", "no 10 €"),
         ("Matu krāsošana", "", "no 40 €"), ("Šķipsnu balināšana", "", "no 55 €"), ("Svētku frizūra", "", "no 35 €")]),
    "vet": ("Veterinārā klīnika", "Jūsu mīlulis <em>drošās rokās</em>",
        "Vakcinācija, ārstēšana un operācijas. Pirms ārstēšanas izskaidrojam, kas notiks un cik tas maksās.",
        [("Apskate un konsultācija", "20,00"), ("Vakcinācija", "25,00"), ("Ieraksts dzīvnieka pasē", "0,00"), ("Kopā", "45,00")],
        None, "Cenu piemēri. Precīzas izmaksas nosaucam pēc apskates.",
        [("Apskate un konsultācija", "", "no 20 €"), ("Vakcinācija", "", "no 25 €"), ("Mikročipa ievietošana", "", "no 20 €"),
         ("Kastrācija, kaķis", "", "no 40 €"), ("Sterilizācija, kaķene", "", "no 60 €"), ("Zobakmens tīrīšana", "", "no 50 €")]),
    "buve": ("Būvniecība un remonts", "Būvdarbi ar <em>tāmi un termiņu</em>",
        "Pirms darba saņemat tāmi un termiņu. Par izmaiņām vienojamies, pirms tās veicam.",
        [("Vannas istabas flīzēšana, 12 m²", "480,00"), ("Flīžu līme un šuvotājs", "95,00"), ("Objekta apskate", "0,00"), ("Kopā ar PVN", "575,00")],
        None, "Cenu piemēri. Precīzu tāmi sagatavojam pēc objekta apskates.",
        [("Flīzēšana", "Par kvadrātmetru", "no 35 €"), ("Sienu špaktelēšana un krāsošana", "Par kvadrātmetru", "no 12 €"),
         ("Lamināta ieklāšana", "Par kvadrātmetru", "no 8 €"), ("Mūrēšanas darbi", "", "pēc tāmes"),
         ("Jumta seguma maiņa", "", "pēc tāmes")]),
    "meistars": ("Santehnika, apkure un elektrība", "Meistars, kas ierodas norunātajā laikā",
        "Pirms darba nosaucam cenu. Ja darba laikā atklājas vēl kas, vispirms vienojamies un tikai tad darām.",
        [("Ūdens sildītāja nomaiņa", "90,00"), ("Pievienojumi un materiāli", "45,00"), ("Izbraukums pilsētā", "0,00"), ("Kopā ar PVN", "135,00")],
        ("Apkures sezona", "Katla un radiatoru apkopi labāk veikt laikus, pirms sals."),
        "Cenu piemēri. Precīzu cenu nosaucam pēc apskates.",
        [("Izsaukums un apskate", "", "no 25 €"), ("Santehnikas remonts", "Par stundu", "no 30 €"),
         ("Kontaktligzdas vai slēdža maiņa", "", "no 15 €"), ("Elektroinstalācija dzīvoklī", "", "pēc tāmes"),
         ("Apkures katla apkope", "", "no 60 €"), ("Kanalizācijas tīrīšana", "", "no 40 €")]),
}

# first matching keyword picks the card icon and the one-line description
KINDS = [
    ("higiēn", "shield", "Saudzīgi un bez steigas."),
    ("balināš", "check", "Vispirms pārbaudām, vai balināšana jums ir piemērota."),
    ("implant", "tooth", "Pastāstām par norisi, termiņiem un izmaksām, pirms izlemjat."),
    ("protez|kron", "tooth", "Piemeklējam risinājumu jūsu situācijai un budžetam."),
    ("rentgen", "doc", "Uzņēmumu izskaidrojam saprotami un parādām, ko tajā redzam."),
    ("ķirurģ|izrauš", "tooth", "Izskaidrojam norisi un to, kā rūpēties pēc tam."),
    ("bērn", "chat", "Nesteidzamies un ļaujam bērnam pierast."),
    ("plomb|zob", "tooth", "Pirms ārstēšanas izskaidrojam, kas tiks darīts un cik tas maksās."),
    ("zārk|piederum|urn", "check", "Palīdzam izvēlēties atbilstoši jūsu vēlmēm un iespējām."),
    ("transport|katafalk|pārvešan", "truck", "Zvaniet, vienosimies par laiku un vietu."),
    ("dokument", "doc", "Pastāstām, kas vajadzīgs, un palīdzam nokārtot."),
    ("kremāc|kap|rakšan|piemin|ceremon|izvadī|atvad|bēru org|apbedīš|morg|rīkoš", "clock", "Uzņemamies organizēšanu, lai jums par to nebūtu jādomā."),
    ("konfekš|dāvan|suvenīr", "gift", "Sīkumi, ko pielikt pie ziediem, lai dāvana būtu pilnīga."),
    ("telpaug|stād|podiņ", "drop", "Palīdzam izvēlēties un pastāstām, kā kopt."),
    ("sēr|vaiņag|vainag", "flower", "Izgatavojam pēc pasūtījuma, arī steidzami."),
    ("kāz|svētk|dekor|noform", "gift", "Uzrakstiet datumu un ieceri, un sagatavosim piedāvājumu."),
    ("piegād", "truck", "Piegādājam norunātajā laikā un vietā."),
    ("kompozīc", "gift", "Galdam, dāvanai vai telpas noformējumam."),
    ("pušķ|zied|rozes|flor", "flower", "Svaigi ziedi un pušķi pēc jūsu vēlmēm un budžeta."),
    ("banket|mielast|izbraukum|svinīb|klāšan", "utensils", "Ēdienkarti un cenu vienai personai saskaņojam iepriekš."),
    ("pusdien|ēdien|ēdin|virtuv|līdzņem|brokast|uzkod", "utensils", "Gatavojam uz vietas no svaigiem produktiem."),
    ("kafij|kūk|konditor|desert", "cup", "Uz vietas vai līdzņemšanai."),
    ("zāle|telpas", "pin", "Telpas jūsu pasākumam. Viesu skaitu saskaņojam iepriekš."),
    ("dzinēj|motor", "wrench", "Vispirms atrodam cēloni, tad nosaucam remonta cenu."),
    ("diagnost", "gauge", "Nolasām kļūdas un saprotami izskaidrojam, ko tās nozīmē."),
    ("riep", "tyre", "Maiņa, montāža un balansēšana, piesakoties iepriekš."),
    ("savirz|ģeometr", "tyre", "Noregulējam, lai auto brauktu taisni un riepas nodiltu vienmērīgi."),
    ("kondicion", "snow", "Pārbaude, uzpilde un remonts pirms sezonas."),
    ("kravas|autobus|evakuator|palīdzība", "truck", "Zvaniet, vienosimies par laiku un vietu."),
    ("elektr|starter|ģenerator", "bolt", "Atrodam vainu un salabojam, nevis mainām visu pēc kārtas."),
    ("krāso|virsbūv|pretrūs|stikl", "shield", "Rūpīgs darbs, kas pasargā auto un saglabā tā vērtību."),
    ("apkop|eļļ|apskat", "drop", "Regulāra apkope, lai lielie remonti nebūtu vajadzīgi."),
]

# ---- look: every business gets its own mix of layout, typeface, colours, corner shape and photo, picked from its
# slug so it never changes between builds. Trades keep a fitting tone (workshop, soft, clinical).
def pick(slug, salt, n):
    return zlib.crc32(f"{salt}/{slug}".encode()) % n


TONE = {"ziedi": "soft", "kafe": "soft", "friz": "soft", "beres": "soft", "zobi": "clean", "vet": "clean"}
BG = {"ziedi": "#faf6f1", "kafe": "#faf5ee", "zobi": "#f3f8f9", "beres": "#f6f5f2", "friz": "#faf6f4", "vet": "#f3f8f6"}
# band, band-2, signal, text on signal
PALETTES = {
    "auto": [("#14262b", "#1c343a", "#f2b705", "#1b1602"), ("#14262b", "#1c343a", "#ff7a1a", "#1f0e00"), ("#131b2e", "#22325a", "#f2b705", "#1b1602"),
             ("#1b1d1f", "#2e3338", "#ff5a4d", "#1a0000"), ("#14262b", "#1c343a", "#7ed957", "#0d1f05"), ("#102a2a", "#1b4a47", "#ffd166", "#1b1602")],
    "buve": [("#1f2428", "#39424a", "#ffb000", "#1b1300"), ("#22302a", "#34493f", "#e8c547", "#1c1702"), ("#2b1f1a", "#46302a", "#f08a4b", "#210d00"),
             ("#18233a", "#263a5e", "#ffb000", "#1b1300")],
    "meistars": [("#13283a", "#1f3d57", "#4cc2ff", "#04202f"), ("#0f2e33", "#1a4a50", "#5eead4", "#03302a"), ("#1e2329", "#333b45", "#ff8a3d", "#220e00"),
                 ("#1a1f3d", "#2b3261", "#9db8ff", "#0a1338")],
    "zobi": [("#123a4a", "#1d5a70", "#8fe0d0", "#06302b"), ("#1b2b4b", "#2b4474", "#a9cbff", "#0a1c3d"), ("#14403a", "#20625a", "#c2ebae", "#0f2a06"),
             ("#2d2a4a", "#454073", "#cdbdff", "#1a1140")],
    "vet": [("#0f3d3e", "#1b605d", "#ffc857", "#2a1c00"), ("#24382b", "#365441", "#f4a259", "#2a1200"), ("#1f3050", "#30497a", "#ffd166", "#2a1c00")],
    "ziedi": [("#20392f", "#2e5244", "#f4b6c2", "#3a1420"), ("#3a2233", "#57334d", "#f2c6a0", "#3a1c05"), ("#2c3327", "#434d3b", "#ead98f", "#2a2405"),
              ("#4a2a2f", "#6b3d44", "#f6cfd3", "#3a1420")],
    "kafe": [("#2a1c14", "#46301f", "#e9a23b", "#2a1602"), ("#1f2a24", "#31423a", "#e6c28b", "#2a1c05"), ("#331a1a", "#512a2a", "#f0b27a", "#2a1202")],
    "beres": [("#1f2326", "#343b40", "#cdb88f", "#1f1a10"), ("#23262b", "#3a3f47", "#b9c4cf", "#12181f")],
    "friz": [("#2b2230", "#4a3352", "#f0b9a4", "#2b1410"), ("#1f2a2e", "#31434a", "#f2c9a8", "#2b1705"), ("#33222a", "#523643", "#f3b8c8", "#33101c")],
}
_T = 'h1,h2,.brand,form h3{text-transform:none;letter-spacing:%s;font-weight:%s}h1{font-size:clamp(%s);line-height:%s}h2{line-height:1.14}.brand{font-size:%s}'
# Google Fonts family, CSS font stack, heading rules (all cover Latvian letters)
FONTS = {
    "tech": [("Barlow+Condensed:wght@600;700", '"Barlow Condensed","Arial Narrow",Arial,sans-serif', ""),
             ("Archivo:wght@700;800", '"Archivo",Arial,sans-serif', _T % ("-.02em", "800", "2.2rem,5.4vw,3.8rem", "1.04", "1.25rem")),
             ("Bitter:wght@600;700", '"Bitter",Georgia,serif', _T % ("-.01em", "700", "2.1rem,5vw,3.5rem", "1.1", "1.25rem")),
             ("Sora:wght@600;700", '"Sora",Arial,sans-serif', _T % ("-.03em", "700", "2rem,4.8vw,3.3rem", "1.1", "1.2rem"))],
    "soft": [("Playfair+Display:wght@600;700", '"Playfair Display",Georgia,serif', _T % ("0", "700", "2.3rem,6vw,4rem", "1.08", "1.3rem")),
             ("Fraunces:wght@500;600", '"Fraunces",Georgia,serif', _T % ("-.01em", "600", "2.3rem,5.8vw,3.9rem", "1.06", "1.3rem")),
             ("DM+Serif+Display", '"DM Serif Display",Georgia,serif', _T % ("0", "400", "2.4rem,6vw,4.1rem", "1.06", "1.35rem")),
             ("Lora:wght@600;700", '"Lora",Georgia,serif', _T % ("-.005em", "700", "2.2rem,5.4vw,3.7rem", "1.1", "1.3rem"))],
    "clean": [("", "var(--body)", _T % ("-.01em", "600", "2.2rem,5.6vw,3.7rem", "1.1", "1.25rem")),
              ("Manrope:wght@700;800", '"Manrope",Arial,sans-serif', _T % ("-.03em", "800", "2.1rem,5.2vw,3.5rem", "1.08", "1.25rem")),
              ("Sora:wght@600;700", '"Sora",Arial,sans-serif', _T % ("-.03em", "700", "2rem,4.8vw,3.3rem", "1.1", "1.2rem")),
              ("Plus+Jakarta+Sans:wght@700;800", '"Plus Jakarta Sans",Arial,sans-serif', _T % ("-.03em", "800", "2.1rem,5.2vw,3.5rem", "1.08", "1.25rem"))],
}
SHAPES = {"tech": [":root{--r:0}", ":root{--r:2px}", ":root{--r:4px}"],  # small corners only: big rounding and pill buttons read as AI-made
          "soft": [":root{--r:6px}", ":root{--r:4px}", ":root{--r:6px}"],
          "clean": [":root{--r:2px}", ":root{--r:4px}", ":root{--r:6px}"]}
_BG = ('.hero-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:-3;animation:zoom 16s ease-out both}'
       '@keyframes zoom{from{scale:1.1}}')
# hero layouts. "klasika" is the template as it is (sample estimate in the hero).
DESIGNS = {
    "klasika": "",
    # photo across the whole hero, text on the darker side
    "foto": _BG + ('.hero::before{z-index:-1;background:linear-gradient(90deg,color-mix(in srgb,var(--band) 96%,transparent),color-mix(in srgb,var(--band) 80%,transparent) 46%,'
                   'color-mix(in srgb,var(--band) 16%,transparent));-webkit-mask-image:none;mask-image:none}'
                   '.hero .wrap{grid-template-columns:1fr;padding-block:clamp(72px,10vw,140px) clamp(120px,13vw,170px)}.hero .wrap>div{max-width:620px}'),
    # centred text over a dimmed photo
    "centrs": _BG + ('.hero::before{z-index:-1;background:color-mix(in srgb,var(--band) 76%,transparent);-webkit-mask-image:none;mask-image:none}'
                     '.hero .wrap{grid-template-columns:1fr;justify-items:center;text-align:center;padding-block:clamp(84px,12vw,160px) clamp(130px,14vw,180px)}'
                     '.hero .wrap>div{max-width:720px}.hero .lead,.tagline{margin-inline:auto}.cta-row{justify-content:center}'),
    # light header and hero, framed photo with a colour block behind it
    "gaiss": ('.top{background:var(--surface);color:var(--ink);border-bottom-color:var(--line)}.hero{background:var(--surface);color:var(--ink)}'
              '.hero::before{display:none}.hero .wrap{grid-template-columns:1fr 1fr;padding-bottom:clamp(104px,11vw,140px)}'
              '.hero-fig{margin:0;position:relative;aspect-ratio:5/4;isolation:isolate}'
              '.hero-fig::before{content:"";position:absolute;inset:20px -20px -20px 20px;background:var(--signal);border-radius:calc(var(--r)*2);z-index:-1;animation:rise .9s .5s var(--ease) both}'
              '.hero-fig img{display:block;width:100%;height:100%;object-fit:cover;border-radius:calc(var(--r)*2);animation:wipe 1.1s .2s var(--ease) both}'
              '@keyframes wipe{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}'
              '@media(max-width:900px){.hero .wrap{grid-template-columns:1fr}.hero-fig{aspect-ratio:16/10}.hero-fig::before{inset:12px -10px -12px 12px}}'),
    # split screen: text on the colour, photo to the edge of the window
    "ramis": ('.hero::before{display:none}.hero .wrap{max-width:none;padding:0;grid-template-columns:1fr 1fr;gap:0;align-items:stretch}'
              '.hero .wrap>div{align-self:center;padding:clamp(52px,7vw,100px) clamp(24px,5vw,72px) clamp(104px,11vw,140px) max(20px,calc(50vw - 540px))}'
              '.hero-fig{margin:0;position:relative;min-height:440px;overflow:hidden}'
              '.hero-fig img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;animation:zoom 16s ease-out both}@keyframes zoom{from{scale:1.1}}'
              '.hero-fig::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,var(--band),transparent 35%)}'
              '@media(max-width:900px){.hero .wrap{grid-template-columns:1fr}.hero .wrap>div{padding:44px 20px 36px}.hero-fig{min-height:280px}'
              '.hero-fig::after{background:linear-gradient(180deg,var(--band),transparent 35%)}}'),
    # the trade drawing draws itself next to the headline
    "zimejums": ('.hero .art{width:min(100%,440px);margin:0 auto;opacity:.95;stroke-width:1.5}'
                 '.hero .art *{stroke-dashoffset:1;transition:none;animation:draw 2.6s .4s cubic-bezier(.6,0,.2,1) forwards}'
                 '.hero .art :nth-child(n+4){animation-delay:.9s}.hero .art :nth-child(n+7){animation-delay:1.3s}@keyframes draw{to{stroke-dashoffset:0}}'
                 '.why .wrap{grid-template-columns:1fr}.why-head{position:static}.why ul{display:grid;grid-template-columns:1fr 1fr;gap:0 48px}'
                 '.why li:nth-last-child(-n+2){border-bottom:1px solid rgb(255 255 255/.14)}'
                 '@media(max-width:900px){.hero .art{width:230px;margin:0}.why ul{grid-template-columns:1fr}}'),
}
MIRROR = {"klasika": ('@media(min-width:901px){.hero .wrap{grid-template-columns:.85fr 1.15fr}.hero .wrap>div{order:2}'
                      '.hero::before{-webkit-mask-image:linear-gradient(255deg,transparent 35%,#000);mask-image:linear-gradient(255deg,transparent 35%,#000)}}'),
          "gaiss": '@media(min-width:901px){.hero .wrap>div{order:2}.hero-fig::before{inset:20px 20px -20px -20px}}',
          "zimejums": '@media(min-width:901px){.hero .wrap>div{order:2}}'}
# services as a list with dividers instead of cards
ROWS = ('.cards{display:block;border-top:1px solid var(--line)}'
        '.cards li{display:grid;grid-template-columns:34px minmax(0,1fr) minmax(0,1.3fr);gap:6px 22px;align-items:center;padding:20px 4px;background:none;border:0;'
        'border-bottom:1px solid var(--line);border-radius:0}.cards .ico,.cards p{margin:0}'
        '.cards .more{display:flex;margin-top:22px;padding:24px;border-radius:var(--r);background:var(--band)}.cards .more:hover{translate:none}'
        '@media(max-width:640px){.cards li{grid-template-columns:34px 1fr}.cards li p{grid-column:2}}')
DESIGNS_FOR = {"tech": ["klasika", "foto", "ramis", "zimejums", "gaiss"], "soft": ["centrs", "gaiss", "foto", "ramis", "zimejums"],
               "clean": ["gaiss", "ramis", "foto", "zimejums", "klasika"]}
# free stock photos in assets/foto/<set>-1..3.jpg, shown as examples until the owner sends their own
PHOTOSET = dict.fromkeys(["auto", "riepas", "virsbuve", "stikli", "gaze", "karbas", "sture", "dizelis", "prets"], "auto")
PHOTOSET.update(meistars="meistars", apkure="meistars", jumti="jumti", buve="buve", elektro="elektro", zobi="zobi", ziedi="ziedi", kafe="kafe", vet="vet")
KEEP_LOOK = {"autoserviss", "bergs-serviss", "rem-sport"}  # pages already sent out keep their colours and layout
GENERIC_LOOK = {"buvfirma": ("ramis", "jumti"), "ziedu-salons": ("centrs", "ziedi"), "kafejnica": ("foto", "kafe"), "zobarstnieciba": ("gaiss", "zobi"),
                "frizetava": ("zimejums", None), "veterinara-klinika": ("foto", "vet"), "apbedisanas-birojs": ("klasika", None)}


def look(slug, prof, vkey, generic):
    tone, pals = TONE.get(prof, "tech"), PALETTES.get(prof) or PALETTES["auto"]
    photos = PHOTOSET.get(vkey or prof)
    fi = pi = si = 0
    mirror = rows = swap = False
    if slug in KEEP_LOOK:
        design, si, photos = "klasika", None, None
    elif generic:
        design, photos = GENERIC_LOOK[slug]
    else:
        options = [d for d in DESIGNS_FOR[tone] if photos or d in ("klasika", "zimejums")]
        design = options[pick(slug, "d43", len(options))]
        fi, pi, si = pick(slug, "f", len(FONTS[tone])), pick(slug, "p", len(pals)), pick(slug, "s", len(SHAPES[tone]))
        mirror, rows, swap = pick(slug, "m", 2) == 1, pick(slug, "r", 3) == 0, pick(slug, "o", 2) == 1
    gf, family, fcss = FONTS[tone][fi]
    band, band2, signal, on = pals[pi]
    css = f":root{{--band:{band};--band-2:{band2};--signal:{signal};--on-signal:{on};--display:{family}}}"
    if prof in BG:
        css += f"@media(prefers-color-scheme:light){{:root{{--bg:{BG[prof]}}}}}"
    css += fcss + (SHAPES[tone][si] if si is not None else "") + DESIGNS[design] + (MIRROR.get(design, "") if mirror else "") + (ROWS if rows else "")
    first = pick(slug, "foto", 3)
    return dict(design=design, css=css, gf=gf, swap=swap,
                photos=[f"{photos}-{(first + i) % 3 + 1}" for i in range(3)] if photos else [])


def apply_look(page, L, drawing, assets):
    """Rearrange the built page for its design: hero picture or drawing, sample estimate, photo row, section order."""
    page = page.replace("&family=Barlow+Condensed:wght@600;700", f"&family={L['gf']}" if L["gf"] else "")
    page = page.replace("</style>\n<script>if (/[?&]still/", f"</style>\n<style>{L['css']}</style>\n<script>if (/[?&]still/", 1)
    d, ph = L["design"], L["photos"]
    if d != "klasika":
        m = re.search(r'    <aside class="estimate".*?</aside>\n', page, flags=re.S)
        if d in ("foto", "centrs"):
            media = ""
            page = page.replace('<section class="hero">\n', f'<section class="hero">\n  <img class="hero-bg" src="{assets}{ph[0]}.jpg" alt="" fetchpriority="high">\n', 1)
        elif d == "zimejums":
            media = drawing.replace("      <svg", "    <svg", 1)
        else:
            media = f'    <figure class="hero-fig"><img src="{assets}{ph[0]}.jpg" alt="" fetchpriority="high"></figure>\n'
        page = page.replace(m.group(0), media, 1)
        est = m.group(0).replace("    <aside", "      <aside", 1).replace("    </aside>", "      </aside>", 1)
        page = page.replace('    </div>\n    <div class="prices rv">', est + '    </div>\n    <div class="prices rv">', 1)
    if ph:  # two example photos, the third box stays "your photo here"
        used = ph[1:] if d != "klasika" and d != "zimejums" else ph[:2]
        boxes = iter(used)
        def box(m):
            p = next(boxes, None)
            return f'<figure><img src="{assets}{p}-s.jpg" alt="" loading="lazy"></figure>' if p else '<div><svg class="i"><use href="#cam"/></svg>Šeit būs jūsu foto</div>'
        page = re.sub(r'(<div class="shots"[^>]*>\n)(.*?)(    </div>\n)',
                      lambda m: m.group(1) + re.sub(r"<div>.*?</div>", box, m.group(2)) + m.group(3)
                      + '    <p class="shots-note">Foto ir piemēri. Īstajā lapā būs jūsu pašu foto.</p>\n', page, count=1, flags=re.S)
        page = page.replace("Teksti un cenas ir piemēri", "Teksti, cenas un foto ir piemēri").replace("teksti un cenas ir piemēri", "teksti, cenas un foto ir piemēri")
        page = page.replace("teksti, cenas un kontakti ir piemēri", "teksti, cenas, foto un kontakti ir piemēri")
    if L["swap"]:  # prices before "how we work"
        m = re.search(r'<section id="cenas">.*?</section>\n\n', page, flags=re.S)
        page = page.replace(m.group(0), "", 1).replace('<section class="why">', m.group(0).replace('<section id="cenas">', '<section id="cenas" class="alt">', 1) + '<section class="why">', 1)
    return page

# trades that are not car shops: own colours, schema.org type, wording swaps and FAQ
EXTRA = {
    "ziedi": dict(
        ld="Florist", generic="Paraugs ziedu salona mājaslapai.",
        swaps=[
            ("Kad salūst auto, cilvēki meklē", "Kad vajag ziedus, cilvēki meklē"),
            ("Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.", "Pirms brauciena cilvēks grib redzēt, ka salons ir īsts un kādi ir pušķi."),
            ("Pieteikt vizīti", "Pasūtīt ziedus"), ("Tāme pirms darba</li>", "Svaigi ziedi</li>"), ("Skaidras cenas</li>", "Pušķi pēc pasūtījuma</li>"),
            ("Tāmes paraugs", "Pasūtījuma paraugs"),
            ("Šādu tāmi saņemat pirms darba. Gala rēķins to nepārsniedz bez jūsu piekrišanas.", "Cenu zināt, pirms pasūtāt. Pušķi saskaņojam ar jūsu vēlmēm un budžetu."),
            ("Ja vajadzīgā darba sarakstā nav, piezvaniet.", "Ja vajadzīgā nav sarakstā, uzrakstiet vai piezvaniet."),
            ("Godīgi, saprotami, laikā", "Svaigi, skaisti, laikā"),
            ("<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>", "<h3>Svaigi ziedi</h3><p>Ziedus saņemam regulāri, tāpēc pušķis priecē ilgāk.</p>"),
            ("<h3>Skaidrojam vienkārši</h3><p>Pasakām, kas jādara tagad un kas var pagaidīt līdz nākamajai reizei.</p>", "<h3>Pušķis jūsu budžetam</h3><p>Nosauciet summu un gadījumu, un piedāvāsim variantus.</p>"),
            ("<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>", "<h3>Gatavs norunātajā laikā</h3><p>Pasūtījums jūs gaida, kad atnākat. Nav jāstāv rindā.</p>"),
            ("<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>", "<h3>Padoms kopšanai</h3><p>Pastāstām, kā rūpēties par ziediem un telpaugiem.</p>"),
            ("Saņemt tāmi savam auto", "Pasūtīt pušķi"),
            ("<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>", "<h3>Pasūtiet</h3><p>Uzrakstiet vai piezvaniet un pastāstiet, kam ziedi domāti un kāds ir budžets.</p>"),
            ("<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>", "<h3>Saskaņojam</h3><p>Piedāvājam variantus un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>"),
            ("<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>", "<h3>Saņemiet ziedus</h3><p>Pušķis ir gatavs norunātajā laikā.</p>"),
            ("Šeit būs jūsu servisa foto", "Šeit būs jūsu pušķu foto"), (">Darbnīca<", ">Salons<"),
            ("jūsu servisa atrašanās vietu", "jūsu salona atrašanās vietu"),
            ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Kam ziedi domāti?<input id="f-car" placeholder="Piemēram, dzimšanas diena, līdz 30 €">'),
            ("Kas jāizdara?", "Jūsu vēlmes"),
        ],
        faq=[("Vai pušķi jāpasūta iepriekš?", "Vēlams, īpaši svētkos un lielākiem pasūtījumiem. Gatavi pušķi salonā ir katru dienu."),
             ("Vai varat izveidot pušķi konkrētai summai?", "Jā. Nosauciet budžetu un gadījumu, un piedāvāsim variantus."),
             ("Cik ilgi ziedi stāvēs?", "Atkarīgs no ziediem. Pie katra pušķa pastāstām, kā to kopt, lai tas priecētu pēc iespējas ilgāk."),
             ("Vai noformējat arī pasākumus?", "Uzrakstiet datumu, vietu un ieceri, un atbildēsim, ko varam piedāvāt.")]),
    "kafe": dict(
        ld="Restaurant", generic="Paraugs kafejnīcas mājaslapai.",
        swaps=[
            ("Kad salūst auto, cilvēki meklē", "Kad cilvēki plāno svinības vai meklē, kur paēst, viņi Google ieraksta"),
            ("Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.", "Pirms brauciena cilvēks grib redzēt ēdienkarti, cenas un telpas."),
            ("Pieteikt vizīti", "Pieteikt pasākumu"), ("Tāme pirms darba</li>", "Gatavojam uz vietas</li>"), ("Skaidras cenas</li>", "Banketi un svinības</li>"),
            ("Tāmes paraugs", "Dienas piedāvājums"),
            ("Šādu tāmi saņemat pirms darba. Gala rēķins to nepārsniedz bez jūsu piekrišanas.", "Cenas redzat iepriekš, bez pārsteigumiem pie kases."),
            ("Ja vajadzīgā darba sarakstā nav, piezvaniet.", "Ja vajadzīgā nav sarakstā, uzrakstiet vai piezvaniet."),
            ("Godīgi, saprotami, laikā", "Garšīgi, mājīgi, laikā"),
            ("<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>", "<h3>Gatavojam paši</h3><p>Ēdienu gatavojam uz vietas, nevis uzsildām.</p>"),
            ("<h3>Skaidrojam vienkārši</h3><p>Pasakām, kas jādara tagad un kas var pagaidīt līdz nākamajai reizei.</p>", "<h3>Cena zināma iepriekš</h3><p>Banketa cenu vienai personai saskaņojam, pirms apstiprināt pasūtījumu.</p>"),
            ("<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>", "<h3>Viss norunātajā laikā</h3><p>Galds ir klāts, kad ierodas viesi.</p>"),
            ("<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>", "<h3>Pielāgojam ēdienkarti</h3><p>Veģetārie un bērnu ēdieni pēc vienošanās.</p>"),
            ("<p class=\"kicker\">Cenrādis</p>\n      <h2>Cenas</h2>", "<p class=\"kicker\">Cenrādis</p>\n      <h2>Ēdienkarte un cenas</h2>"),
            ("Saņemt tāmi savam auto", "Saņemt piedāvājumu"),
            ("<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>", "<h3>Piesakieties</h3><p>Uzrakstiet datumu, viesu skaitu un kāds pasākums plānots.</p>"),
            ("<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>", "<h3>Saņemiet piedāvājumu</h3><p>Atsūtām ēdienkarti un cenu vienai personai. Lēmums paliek jūsu ziņā.</p>"),
            ("<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>", "<h3>Sviniet</h3><p>Galds ir klāts norunātajā laikā. Jums atliek sagaidīt viesus.</p>"),
            ("Šeit būs jūsu servisa foto", "Šeit būs jūsu ēdienu foto"), (">Darbnīca<", ">Zāle<"),
            ("jūsu servisa atrašanās vietu", "jūsu kafejnīcas atrašanās vietu"),
            ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Datums un viesu skaits<input id="f-car" placeholder="Piemēram, 14. decembris, 30 viesi">'),
            ("Kas jāizdara?", "Kāds pasākums plānots?"),
        ],
        faq=[("Vai galdiņš jārezervē iepriekš?", "Pusdienām nav jārezervē. Lielākām kompānijām ieteicams pieteikties iepriekš."),
             ("Cik viesiem varat klāt galdu?", "Atkarīgs no pasākuma. Uzrakstiet viesu skaitu, un atbildēsim, ko varam piedāvāt."),
             ("Vai ir veģetārie ēdieni?", "Jā, pēc vienošanās pielāgojam ēdienkarti arī veģetāriešiem un bērniem."),
             ("Kā notiek apmaksa par banketu?", "Cenu vienai personai saskaņojam iepriekš. Par priekšapmaksu vienojamies, apstiprinot pasūtījumu.")]),
    "zobi": dict(
        ld='Dentist', generic='Paraugs zobārstniecības mājaslapai.',
        swaps=[('Kad salūst auto, cilvēki meklē', 'Kad sāp zobs, cilvēki meklē'), ('Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.', 'Pirms vizītes cilvēks grib redzēt, ka prakse ir īsta, un zināt cenas.'), ('Tāme pirms darba</li>', 'Plāns pirms ārstēšanas</li>'), ('Tāmes paraugs', 'Ārstēšanas plāna paraugs'), ('Šādu tāmi saņemat pirms darba. Gala rēķins to nepārsniedz bez jūsu piekrišanas.', 'Plānu un izmaksas saņemat pirms ārstēšanas. Bez jūsu piekrišanas nekas netiek darīts.'), ('Ja vajadzīgā darba sarakstā nav, piezvaniet.', 'Ja vajadzīgā nav sarakstā, uzrakstiet vai piezvaniet.'), ('Godīgi, saprotami, laikā', 'Saudzīgi, saprotami, laikā'), ('<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>', '<h3>Plāns pirms ārstēšanas</h3><p>Zināt, kas tiks darīts un cik tas maksās, pirms sēžaties krēslā.</p>'), ('<h3>Skaidrojam vienkārši</h3><p>Pasakām, kas jādara tagad un kas var pagaidīt līdz nākamajai reizei.</p>', '<h3>Skaidrojam vienkārši</h3><p>Pastāstām, kas jāārstē tagad un kas var pagaidīt.</p>'), ('<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>', '<h3>Cienām jūsu laiku</h3><p>Pieņemam pēc pieraksta, lai nebūtu jāgaida rindā.</p>'), ('<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>', '<h3>Akūtas sāpes</h3><p>Zvaniet, meklēsim tuvāko brīvo laiku.</p>'), ('Saņemt tāmi savam auto', 'Pieteikt vizīti'), ('<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>', '<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un piedāvājam laiku.</p>'), ('<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>', '<h3>Saņemiet plānu</h3><p>Pēc apskates izskaidrojam, kas jādara, un nosaucam izmaksas. Lēmums paliek jūsu ziņā.</p>'), ('<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>', '<h3>Ārstēšana</h3><p>Ārstēšana notiek pēc saskaņotā plāna. Rēķinā ir tas pats, kas plānā.</p>'), ('Šeit būs jūsu servisa foto', 'Šeit būs jūsu prakses foto'), ('>Darbnīca<', '>Kabinets<'), ('jūsu servisa atrašanās vietu', 'jūsu prakses atrašanās vietu'), ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Vēlamais laiks<input id="f-car" placeholder="Piemēram, darba dienās pēc 17.00">'), ('Kas jāizdara?', 'Kas jūs satrauc?')],
        faq=[('Vai jāpiesakās iepriekš?', 'Jā, pieņemam pēc pieraksta. Akūtu sāpju gadījumā zvaniet, meklēsim tuvāko brīvo laiku.'), ('Cik maksās ārstēšana?', 'Atkarīgs no tā, kas jādara. Pēc apskates saņemat plānu ar izmaksām un tikai tad izlemjat.'), ('Ko darīt, ja ir bail no zobārsta?', 'Pasakiet to piesakoties. Strādājam nesteidzīgi un pirms katra soļa izskaidrojam, kas notiks.'), ('Cik bieži jānāk uz pārbaudi?', 'Parasti reizi pusgadā vai gadā. Pēc apskates ieteiksim, kas piemērots jums.')]),
    "beres": dict(
        ld='LocalBusiness', generic='Paraugs apbedīšanas biroja mājaslapai.',
        swaps=[('Kad salūst auto, cilvēki meklē', 'Kad aiziet tuvinieks, cilvēki meklē'), ('Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.', 'Grūtā brīdī cilvēks grib uzreiz redzēt tālruni, pakalpojumus un izmaksas.'), ('Pieteikt vizīti', 'Sazināties'), ('Tāme pirms darba</li>', 'Skaidras izmaksas</li>'), ('Skaidras cenas</li>', 'Palīdzam ar dokumentiem</li>'), ('Atbilde tajā pašā darba dienā</li>', 'Visi darbi vienuviet</li>'), ('Tāmes paraugs', 'Izmaksu paraugs'), ('Šādu tāmi saņemat pirms darba. Gala rēķins to nepārsniedz bez jūsu piekrišanas.', 'Izmaksas nosaucam uzreiz un pilnībā, bez slēptām pozīcijām.'), ('Ja vajadzīgā darba sarakstā nav, piezvaniet. Pateiksim uzreiz, vai varam palīdzēt.', 'Ja vajadzīgā nav sarakstā, piezvaniet. Pastāstīsim, kā varam palīdzēt.'), ('Godīgi, saprotami, laikā', 'Ar cieņu, mierīgi, bez steigas'), ('<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>', '<h3>Skaidras izmaksas</h3><p>Visu summu zināt iepriekš. Papildu rēķinu pēc bērēm nav.</p>'), ('<h3>Skaidrojam vienkārši</h3><p>Pasakām, kas jādara tagad un kas var pagaidīt līdz nākamajai reizei.</p>', '<h3>Izskaidrojam, kas jādara</h3><p>Pastāstām, kādi dokumenti vajadzīgi un kādā secībā viss notiek.</p>'), ('<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>', '<h3>Viss vienuviet</h3><p>Jums nav jāmeklē vairāki uzņēmumi. Saskaņojam visu vienā sarunā.</p>'), ('<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>', '<h3>Ar cieņu</h3><p>Atvadas organizējam tā, kā to vēlas tuvinieki.</p>'), ('<p class="kicker">Cenrādis</p>\n      <h2>Cenas</h2>', '<p class="kicker">Cenrādis</p>\n      <h2>Pakalpojumi un cenas</h2>'), ('Saņemt tāmi savam auto', 'Uzzināt izmaksas'), ('<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>', '<h3>Piezvaniet</h3><p>Pastāstiet, kas noticis. Izskaidrosim, kas jādara vispirms.</p>'), ('<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>', '<h3>Vienojamies</h3><p>Kopā izvēlamies visu nepieciešamo un nosaucam pilnas izmaksas.</p>'), ('<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>', '<h3>Mēs nokārtojam</h3><p>Uzņemamies organizēšanu, lai jūs varētu būt kopā ar tuviniekiem.</p>'), ('Šeit būs jūsu servisa foto', 'Šeit būs jūsu biroja foto'), ('>Darbnīca<', '>Atvadu zāle<'), ('>Komanda<', '>Transports<'), ('jūsu servisa atrašanās vietu', 'jūsu biroja atrašanās vietu'), ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Kad jums piezvanīt?<input id="f-car" placeholder="Piemēram, šodien pēc 15.00">'), ('Kas jāizdara?', 'Kā varam palīdzēt?'), ('Atbildēsim tajā pašā darba dienā.', 'Atbildēsim, cik ātri vien iespējams.')],
        faq=[('Kas jādara vispirms?', 'Piezvaniet mums. Izskaidrosim, kādi dokumenti vajadzīgi, un palīdzēsim tos nokārtot.'), ('Cik maksā bēres?', 'Atkarīgs no jūsu izvēles. Pilnas izmaksas nosaucam sarunā, pirms kaut ko pasūtāt.'), ('Vai palīdzat ar dokumentiem apbedīšanas pabalstam?', 'Jā. Pastāstām, kādi dokumenti jāiesniedz un kur.'), ('Vai organizējat arī kremāciju?', 'Piezvaniet vai uzrakstiet, un pastāstīsim par iespējām.')]),
    "friz": dict(
        ld='HairSalon', generic='Paraugs frizētavas mājaslapai.',
        swaps=[('Kad salūst auto, cilvēki meklē', 'Kad vajag frizieri, cilvēki meklē'), ('Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.', 'Pirms pieraksta cilvēks grib redzēt cenas un darbu piemērus.'), ('Pieteikt vizīti', 'Pierakstīties'), ('Tāme pirms darba</li>', 'Cenas zināmas iepriekš</li>'), ('Skaidras cenas</li>', 'Pieraksts arī vakarā</li>'), ('Tāmes paraugs', 'Apmeklējuma paraugs'), ('Šādu tāmi saņemat pirms darba. Gala rēķins to nepārsniedz bez jūsu piekrišanas.', 'Cenu zināt, pirms sēžaties krēslā.'), ('Ja vajadzīgā darba sarakstā nav, piezvaniet.', 'Ja vajadzīgā nav sarakstā, uzrakstiet vai piezvaniet.'), ('Godīgi, saprotami, laikā', 'Skaisti, mierīgi, laikā'), ('<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>', '<h3>Cena zināma iepriekš</h3><p>Pirms darba pasakām, cik tas maksās jūsu matu garumam.</p>'), ('<h3>Skaidrojam vienkārši</h3><p>Pasakām, kas jādara tagad un kas var pagaidīt līdz nākamajai reizei.</p>', '<h3>Uzklausām</h3><p>Vispirms pārrunājam, ko vēlaties, un tikai tad ķeramies pie šķērēm.</p>'), ('<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>', '<h3>Bez rindas</h3><p>Strādājam pēc pieraksta, tāpēc nav jāgaida.</p>'), ('<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>', '<h3>Padoms kopšanai</h3><p>Pastāstām, kā saglabāt rezultātu mājās.</p>'), ('Saņemt tāmi savam auto', 'Pierakstīties'), ('<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>', '<h3>Pierakstieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un piedāvājam laiku.</p>'), ('<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>', '<h3>Pārrunājam</h3><p>Uzklausām jūsu vēlmes un nosaucam cenu.</p>'), ('<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>', '<h3>Baudiet rezultātu</h3><p>Aizejat ar frizūru, kādu gribējāt.</p>'), ('Šeit būs jūsu servisa foto', 'Šeit būs jūsu darbu foto'), ('>Darbnīca<', '>Salons<'), ('jūsu servisa atrašanās vietu', 'jūsu salona atrašanās vietu'), ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Vēlamais laiks<input id="f-car" placeholder="Piemēram, sestdien no rīta">'), ('Kas jāizdara?', 'Kāds pakalpojums vajadzīgs?')],
        faq=[('Vai jāpierakstās iepriekš?', 'Jā, strādājam pēc pieraksta. Ja ir brīvs laiks, pieņemam arī tajā pašā dienā.'), ('Cik maksās krāsošana?', 'Atkarīgs no matu garuma un vēlamā toņa. Cenu nosaucam pirms darba.'), ('Vai pieņemat arī bērnus un vīriešus?', 'Jā. Uzrakstiet vai piezvaniet, un pateiksim brīvos laikus.'), ('Ko darīt, ja nevaru ierasties?', 'Lūdzu, paziņojiet laikus, lai šo laiku varētu piedāvāt citam.')]),
    "vet": dict(
        ld='VeterinaryCare', generic='Paraugs veterinārās klīnikas mājaslapai.',
        swaps=[('Kad salūst auto, cilvēki meklē', 'Kad saslimst mīlulis, cilvēki meklē'), ('Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.', 'Pirms vizītes cilvēks grib redzēt darba laiku, cenas un tālruni.'), ('Tāme pirms darba</li>', 'Izmaksas zināmas iepriekš</li>'), ('Tāmes paraugs', 'Vizītes paraugs'), ('Šādu tāmi saņemat pirms darba. Gala rēķins to nepārsniedz bez jūsu piekrišanas.', 'Izmaksas nosaucam pirms ārstēšanas. Bez jūsu piekrišanas nekas netiek darīts.'), ('Ja vajadzīgā darba sarakstā nav, piezvaniet.', 'Ja vajadzīgā nav sarakstā, uzrakstiet vai piezvaniet.'), ('Godīgi, saprotami, laikā', 'Saudzīgi, saprotami, laikā'), ('<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>', '<h3>Izmaksas iepriekš</h3><p>Pēc apskates pasakām, kas jādara un cik tas maksās.</p>'), ('<h3>Skaidrojam vienkārši</h3><p>Pasakām, kas jādara tagad un kas var pagaidīt līdz nākamajai reizei.</p>', '<h3>Skaidrojam vienkārši</h3><p>Pastāstām, kas mīlulim kaiš un kā par viņu rūpēties mājās.</p>'), ('<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>', '<h3>Pēc pieraksta</h3><p>Mazāk gaidīšanas un mazāk stresa dzīvniekam.</p>'), ('<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>', '<h3>Steidzamie gadījumi</h3><p>Zvaniet, pateiksim, cik ātri varam pieņemt.</p>'), ('Saņemt tāmi savam auto', 'Pieteikt vizīti'), ('<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>', '<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un piedāvājam laiku.</p>'), ('<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>', '<h3>Apskate</h3><p>Izmeklējam dzīvnieku, izskaidrojam, kas jādara, un nosaucam izmaksas. Lēmums paliek jūsu ziņā.</p>'), ('<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>', '<h3>Ārstēšana</h3><p>Ārstējam pēc saskaņotā plāna un pastāstām, kā rūpēties mājās.</p>'), ('Šeit būs jūsu servisa foto', 'Šeit būs jūsu klīnikas foto'), ('>Darbnīca<', '>Kabinets<'), ('jūsu servisa atrašanās vietu', 'jūsu klīnikas atrašanās vietu'), ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Dzīvnieks un vecums<input id="f-car" placeholder="Piemēram, kaķis, 3 gadi">'), ('Kas jāizdara?', 'Kas noticis?')],
        faq=[('Vai jāpiesakās iepriekš?', 'Vēlams. Steidzamos gadījumos zvaniet, pateiksim, cik ātri varam pieņemt.'), ('Cik maksā vakcinācija?', 'Atkarīgs no vakcīnas. Cenu nosaucam piesakoties.'), ('Kas jāņem līdzi uz vizīti?', 'Dzīvnieka pasi vai vakcinācijas apliecību, ja tāda ir.'), ('Vai braucat arī mājas vizītēs?', 'Piezvaniet vai uzrakstiet, un pastāstīsim par iespējām.')]),
    "buve": dict(
        ld="GeneralContractor", generic="Paraugs būvfirmas mājaslapai.",
        swaps=[('Kad salūst auto, cilvēki meklē', 'Kad vajag meistaru, cilvēki meklē'), ('Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.', 'Pirms zvana cilvēks grib redzēt paveiktos darbus un saprast cenu līmeni.'), ('Pieteikt vizīti', 'Saņemt tāmi'), ('<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms atstājat atslēgas. Bez jūsu piekrišanas tā nemainās.</p>', '<h3>Tāme pirms darba</h3><p>Cenu zināt, pirms sākam. Bez jūsu piekrišanas tā nemainās.</p>'), ('<h3>Turam termiņus</h3><p>Nosaucam, kad auto būs gatavs, un paziņojam, ja kas mainās.</p>', '<h3>Turam termiņus</h3><p>Nosaucam, kad darbs būs pabeigts, un paziņojam, ja kas mainās.</p>'), ('<h3>Parādām paveikto</h3><p>Nomainītās detaļas varat apskatīt, saņemot auto.</p>', '<h3>Sakopjam aiz sevis</h3><p>Objektu nododam tīru un būvgružus aizvedam.</p>'), ('Saņemt tāmi savam auto', 'Saņemt tāmi savam objektam'), ('<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par laiku.</p>', '<h3>Piesakieties</h3><p>Zvaniet vai aizpildiet pieteikumu. Atbildam tajā pašā darba dienā un vienojamies par apskati.</p>'), ('<h3>Saņemiet tāmi</h3><p>Apskatām auto, izskaidrojam, kas jādara, un nosaucam cenu. Lēmums paliek jūsu ziņā.</p>', '<h3>Saņemiet tāmi</h3><p>Apskatām objektu, izskaidrojam, kas jādara, un nosaucam cenu un termiņu. Lēmums paliek jūsu ziņā.</p>'), ('<h3>Saņemiet auto</h3><p>Paziņojam, kad auto gatavs. Rēķinā ir tas pats, kas tāmē.</p>', '<h3>Pieņemiet darbu</h3><p>Kopā apskatām paveikto. Rēķinā ir tas pats, kas tāmē.</p>'), ('Šeit būs jūsu servisa foto', 'Šeit būs jūsu darbu foto'), ('>Darbnīca<', '>Objekts<'), ('jūsu servisa atrašanās vietu', 'jūsu biroja atrašanās vietu'), ('Auto marka, modelis un gads<input id="f-car" placeholder="Piemēram, VW Golf, 2014">', 'Kas jādara un kur?<input id="f-car" placeholder="Piemēram, jumta maiņa, Cēsis">'), ('Kas jāizdara?', 'Sīkāks apraksts')],
        faq=[('Kā notiek objekta apskate?', 'Uzrakstiet, kur atrodas objekts, un vienosimies par laiku. Pēc apskates sagatavojam tāmi.'), ('Cik ātri varat sākt?', 'Atkarīgs no sezonas un darba apjoma. Termiņu nosaucam kopā ar tāmi.'), ('Vai materiālus pērkat jūs?', 'Varam nopirkt mēs vai strādāt ar jūsu materiāliem. Tāmē tas ir norādīts atsevišķi.'), ('Kas notiek, ja darba laikā atklājas vēl kas?', 'Darbu apturam un piezvanām. Turpinām tikai tad, kad esat piekritis jaunajai cenai.')]),
}

# trade-specific card texts, checked before the general list
KINDS_BY = {
    "buve": [("uzmēr", "ruler", "Uzmērām uz vietas, lai tāme atbilstu īstajam jumtam."),
             ("jumta log|logi", "window", "Iebūvējam un noblīvējam, lai nepūstu un netecētu."),
             ("notek|skārd|dzeg|palodz", "drop", "Izgatavojam pēc izmēra un uzstādām."),
             ("jumt|skurste", "home", "Palīdzam izvēlēties segumu un ieklājam to."),
             ("kamīn|krāsn|pavard|mūr", "flame", "Būvējam un mūrējam tā, lai labi vilktu un sildītu."),
             ("ūden|kanaliz|apkur|santeh", "drop", "Ierīkojam un pārbaudām, pirms nododam."),
             ("", "wrench", "Tāmi un termiņu nosaucam pirms darba.")],
    "friz": [("manikīr|pedikīr|nag", "check", "Pēc pieraksta, jums ērtā laikā."),
             ("skropst|uzac|kosmet|grims|sejas|vasko|masāž|solārij", "flower", "Pēc pieraksta, jums ērtā laikā."),
             ("", "scissors", "Cenu nosaucam pirms darba, pēc matu garuma un apjoma.")],
    "vet": [("vakcin|čip|pas", "shield", "Vakcinācija, čipēšana un pases noformēšana vienā vizītē."),
            ("ķirurģ|operāc|steriliz|kastr", "check", "Pirms operācijas izskaidrojam norisi un izmaksas."),
            ("zob", "tooth", "Zobakmens tīrīšana un mutes dobuma apskate."),
            ("aptiek|barīb|prec", "gift", "Zāles, barība un kopšanas preces."),
            ("frizēt|kopšan|nag", "scissors", "Kopšana bez steigas un stresa."),
            ("", "clock", "Izmeklējam, izskaidrojam un nosaucam izmaksas pirms ārstēšanas.")],
}

# plumbers, electricians, heating: the construction page with its own wording, colours and card texts
EXTRA["meistars"] = dict(EXTRA["buve"], ld="HomeAndConstructionBusiness",
    generic="Paraugs santehniķa, elektriķa vai apkures meistara mājaslapai.",
    faq=[("Vai braucat arī ārpus pilsētas?", "Jā, novada robežās. Izbraukuma cenu nosaucam, vienojoties par laiku."),
         ("Cik ātri varat ierasties?", "Steidzamos gadījumos cenšamies tajā pašā dienā. Citos gadījumos vienojamies par jums ērtu laiku."),
         ("Vai materiālus atvedat paši?", "Varam atvest mēs vai izmantot jūsu materiālus. To cenu nosaucam atsevišķi."),
         ("Kā ar garantiju?", "Par garantiju vienojamies pirms darba un norādām to rēķinā.")])
KINDS_BY["meistars"] = [("mērīj", "gauge", "Mērījumi ar protokolu, kas vajadzīgs pieslēgumam vai apdrošinātājam."),
                        ("zibens", "shield", "Aprēķinām, uzstādām un pārbaudām."),
                        ("signaliz|apsardz|videonov|vājstr", "eye", "Uzstādām un parādām, kā ar to rīkoties."),
                        ("projekt|tām", "doc", "Sagatavojam projektu un tāmi, pirms sākas darbi."),
                        ("elektr|kabel|apgaism|kontakt|automāt", "bolt", "Ierīkojam, pārbaudām un nododam drošu instalāciju."),
                        ("katl", "flame", "Palīdzam izvēlēties katlu, uzstādām to un noregulējam."),
                        ("radiator", "gauge", "Nomainām un pieslēdzam, pēc tam pārbaudām visu sistēmu."),
                        ("kanaliz|ūden|aku|caurul", "drop", "Ierīkojam un pārbaudām, pirms nododam."),
                        ("santeh", "wrench", "Krāni, podi, dušas un ūdens sildītāji: pieslēdzam un salabojam."),
                        ("ventil|kondic", "snow", "Uzstādām un apkopjam."),
                        ("apkur|siltum|sūkn", "flame", "Apkope un remonts, lai sistēma strādātu visu sezonu."),
                        ("", "wrench", "Cenu nosaucam pirms darba.")]


# hero line drawings (viewBox 400x300), drawn in when the page opens
_ART = {
    "car": '<path d="M45 205H20v-35q0-10 12-13l63-12q25-40 55-45h100q25 0 50 40l60 10q20 3 20 20v35h-30"/><path d="M125 205h145"/>'
           '<path d="M45 205a40 40 0 0 1 80 0"/><path d="M270 205a40 40 0 0 1 80 0"/><circle cx="85" cy="205" r="27"/><circle cx="310" cy="205" r="27"/>'
           '<circle cx="85" cy="205" r="10"/><circle cx="310" cy="205" r="10"/><path d="M128 142q14-27 30-30h42v30z"/><path d="M212 112h33q17 1 35 30h-68z"/><path d="M5 240h390"/>',
    "truck": '<path d="M64 210H30V90h210v120H116"/><path d="M240 125h65l45 40v45h-34"/><path d="M264 210h-24"/><path d="M262 140h36l27 25h-63z"/>'
             '<circle cx="90" cy="210" r="26"/><circle cx="290" cy="210" r="26"/><circle cx="90" cy="210" r="10"/><circle cx="290" cy="210" r="10"/><path d="M10 238h380"/>',
    "house": '<path d="M40 150 200 40l160 110"/><path d="M62 152 200 57l138 95"/><path d="M70 146v114h260V146"/><path d="M270 88V55h30v54"/>'
             '<rect x="110" y="170" width="60" height="50"/><path d="M140 170v50M110 195h60"/><path d="M230 260v-80h55v80"/><path d="M20 260h360"/>',
    "radiator": '<rect x="90" y="80" width="230" height="150" rx="10"/><path d="M123 80v150M156 80v150M189 80v150M222 80v150M255 80v150M288 80v150"/>'
                '<path d="M90 210H50v70"/><path d="M320 100h40v180"/><circle cx="360" cy="160" r="10"/><path d="M112 230v24M298 230v24"/><path d="M20 280h360"/>'
                '<path d="M160 60q10-12 0-24t0-24"/><path d="M205 60q10-12 0-24t0-24"/><path d="M250 60q10-12 0-24t0-24"/>',
    "bulb": '<path d="M200 60a70 70 0 0 1 45 124q-10 10-10 26h-70q0-16-10-26A70 70 0 0 1 200 60z"/><path d="M170 226h60M175 242h50M186 258h28"/>'
            '<path d="M185 210l-10-50 25 20 25-20-10 50"/><path d="M200 18v18"/><path d="M96 74l14 10"/><path d="M304 74l-14 10"/><path d="M62 150h20"/><path d="M318 150h20"/>',
    "tap": '<path d="M110 118h120q42 0 42 42v32"/><path d="M110 152h112q16 0 16 16v24"/><path d="M238 192h34"/><path d="M110 100v70"/><path d="M90 88v94"/>'
           '<path d="M170 118V84"/><path d="M142 84h56"/><path d="M255 214q-15 20 0 31 15-11 0-31z"/><path d="M255 262q-9 13 0 20 9-7 0-20z"/><path d="M60 40v240"/>',
    "flower": '<circle cx="200" cy="100" r="16"/>' + "".join(f'<ellipse cx="200" cy="56" rx="13" ry="26" transform="rotate({a} 200 100)"/>' for a in range(0, 360, 45))
              + '<path d="M200 170c0 40-12 70-4 118"/><path d="M197 222c-37-10-62 5-72 30 35 5 60-5 72-30z"/><path d="M199 196c31-20 63-12 76 10-30 12-60 8-76-10z"/>',
    "cup": '<path d="M110 130h160v55a70 70 0 0 1-70 70h-20a70 70 0 0 1-70-70z"/><path d="M270 145h22a30 30 0 0 1 0 60h-26"/><path d="M80 272h220"/>'
           '<path d="M160 105q10-14 0-28t0-28"/><path d="M190 105q10-14 0-28t0-28"/><path d="M220 105q10-14 0-28t0-28"/>',
    "tooth": '<g transform="translate(92 14) scale(12)" stroke-width=".17"><path d="M7.5 3C5.3 3 4 4.800 4 7.200c0 2 .700 3.300 1.100 5.800.500 3 .700 8 2.400 8 1.700 0 1.200-5.500 2.500-5.500s.800 5.500 2.500 5.500c1.700 0 1.900-5 2.400-8 .400-2.500 1.100-3.800 1.100-5.800C16 4.800 14.700 3 12.500 3 11.300 3 10.800 3.600 10 3.600S8.700 3 7.500 3z"/></g>'
             '<path d="M322 56v40M302 76h40"/><path d="M84 196v26M71 209h26"/>',
    "paw": '<path d="M200 150c40 0 75 35 70 70-4 30-35 25-70 25s-66 5-70-25c-5-35 30-70 70-70z"/><ellipse cx="120" cy="130" rx="22" ry="30" transform="rotate(-25 120 130)"/>'
           '<ellipse cx="172" cy="90" rx="22" ry="32" transform="rotate(-8 172 90)"/><ellipse cx="228" cy="90" rx="22" ry="32" transform="rotate(8 228 90)"/>'
           '<ellipse cx="280" cy="130" rx="22" ry="30" transform="rotate(25 280 130)"/>',
    "scissors": '<circle cx="110" cy="90" r="34"/><circle cx="110" cy="210" r="34"/><path d="M139 108l213 124"/><path d="M131 122l209 126"/>'
                '<path d="M139 192 352 68"/><path d="M131 178 340 52"/><circle cx="232" cy="150" r="5"/>',
    "candle": '<rect x="170" y="130" width="60" height="140" rx="4"/><path d="M200 130v-18"/><path d="M200 105c-18-20-5-43 0-60 5 17 18 40 0 60z"/><path d="M120 270h160"/>',
}
ART_BY = {"buve": "house", "meistars": "tap", "ziedi": "flower", "kafe": "cup", "zobi": "tooth", "vet": "paw", "friz": "scissors",
          "beres": "candle", "kravas": "truck", "evak": "truck"}


def art(key):
    shapes = re.sub(r"<(path|circle|rect|ellipse)\b", r'<\1 pathLength="1"', _ART[key])
    return f'      <svg class="art" viewBox="0 0 400 300" aria-hidden="true">{shapes}</svg>\n'


# variants: a roofer or an electrician gets its own headline, sample estimate and prices instead of the general trade page.
# Picked from the business's own service list; values replace the PROFILES tuple. Prices stay examples.
SEASON_HEAT = ("Apkures sezona", "Katla un radiatoru apkopi labāk veikt laikus, pirms sals.")
VARIANTS = {
    "jumti": dict(art="house", ph="jumta maiņa", prof=(
        "Jumta darbi", "Jumta darbi ar skaidru tāmi un termiņu",
        "Jumtu vispirms apskatām un uzmērām. Tāmi un termiņu saņemat pirms darba, un par izmaiņām vienojamies, pirms tās veicam.",
        [("Lietus ūdens noteku montāža, 24 m", "290,00"), ("Skārda detaļas un stiprinājumi", "140,00"), ("Jumta uzmērīšana", "0,00"), ("Kopā ar PVN", "430,00")],
        ("Jumta apskate pirms ziemas", "Sīkus bojājumus ir vienkāršāk novērst, pirms uzsnieg sniegs."),
        "Cenu piemēri. Precīzu tāmi sagatavojam pēc jumta uzmērīšanas.",
        [("Jumta seguma ieklāšana", "Par kvadrātmetru", "no 12 €"), ("Jumta logu iebūve", "Viens logs", "no 150 €"),
         ("Lietus ūdens noteku montāža", "Par metru", "no 10 €"), ("Skārda detaļu izgatavošana", "", "pēc tāmes"), ("Jumta remonts", "Pēc apskates", "pēc tāmes")])),
    "apkure": dict(art="radiator", ph="katla apkope", prof=(
        "Apkure un santehnika", "Apkure un santehnika ar skaidru cenu",
        "Pirms darba nosaucam cenu. Ja darba laikā atklājas vēl kas, vispirms vienojamies un tikai tad darām.",
        [("Apkures katla apkope", "70,00"), ("Sistēmas atgaisošana un pārbaude", "25,00"), ("Izbraukums", "0,00"), ("Kopā ar PVN", "95,00")],
        SEASON_HEAT, "Cenu piemēri. Precīzu cenu nosaucam pēc apskates.",
        [("Apkures katla apkope", "", "no 60 €"), ("Radiatora maiņa", "Viens radiators", "no 60 €"), ("Ūdens sildītāja nomaiņa", "", "no 90 €"),
         ("Santehnikas remonts", "Par stundu", "no 30 €"), ("Apkures katla uzstādīšana", "Pēc apskates", "pēc tāmes"),
         ("Apkures sistēmas izbūve", "Pēc apskates", "pēc tāmes")])),
    "elektro": dict(art="bulb", ph="jāpārvelk elektroinstalācija", prof=(
        "Elektromontāža", "Elektriķis, kas ierodas norunātajā laikā",
        "Pirms darba nosaucam cenu. Ja darba laikā atklājas vēl kas, vispirms vienojamies un tikai tad darām.",
        [("Kontaktligzdu montāža, 6 gab.", "72,00"), ("Kabelis un materiāli", "38,00"), ("Instalācijas pārbaude", "0,00"), ("Kopā ar PVN", "110,00")],
        None, "Cenu piemēri. Precīzu cenu nosaucam pēc apskates.",
        [("Izsaukums un apskate", "", "no 25 €"), ("Kontaktligzdas vai slēdža maiņa", "", "no 15 €"), ("Gaismekļa pieslēgšana", "", "no 20 €"),
         ("Elektrosadales nomaiņa", "", "pēc tāmes"), ("Elektroinstalācija dzīvoklī vai mājā", "", "pēc tāmes"), ("Elektriskie mērījumi", "", "pēc tāmes")])),
}
PLACEHOLDER = {"buve": "vannas istabas remonts", "meistars": "tek krāns"}  # example in the request form


def variant(prof, services):
    hit = lambda rx: sum(bool(re.search(rx, s.lower())) for s in services)
    if prof == "buve" and hit(r"jumt|skārd|notek|dzeg|palodz") * 2 > len(services):
        return "jumti"
    if prof == "meistars" and hit(r"elektr|vājstr|signaliz|zibens|videonov") * 2 > len(services):
        return "elektro"
    if prof == "meistars" and hit(r"apkur|siltum|katl|radiator"):
        return "apkure"


def card(s, prof="auto", seen=None):
    icon, text = next(((i, t) for k, i, t in KINDS_BY.get(prof, []) + KINDS if re.search(k, s.lower())),
                      ("wrench", "Pirms darba nosaucam cenu un termiņu."))
    if seen is not None:  # the same sentence under every service reads as filler
        text = "" if text in seen else text
        seen.add(text)
    return (f'<li><div class="ico"><svg class="i"><use href="#{icon}"/></svg></div>'
            f'<h3>{html.escape(s)}</h3>{f"<p>{text}</p>" if text else ""}</li>')

for slug, name, loc, town, services, term, *rest in SHOPS:
    if not wanted(slug):
        continue
    prof = rest[0] if rest else "auto"
    vkey = variant(prof, services) if loc else None
    var = VARIANTS.get(vkey, {})
    noun, h1, lead, est, season, price_sub, prices = var.get("prof") or PROFILES[prof]
    h1 = re.sub(r"</?em>", "", h1)
    extra = EXTRA.get(prof, {})
    generic = not loc
    L = look(slug, prof, vkey, generic)
    drawing = art(var.get("art") or ART_BY.get(prof, "car"))
    e = html.escape
    note = (extra.get("generic", "Paraugs autoservisa mājaslapai.") + " Nosaukumu, cenas, foto un kontaktus nomainu pret jūsu."
            if generic else
            f"Šis paraugs ir sagatavots tieši uzņēmumam «{e(name)}». Teksti, cenas, tālrunis un adrese ir piemēri, tos nomainīšu pret jūsējiem.")
    CARD_LI = ("<li><b>Kartīte un mājaslapa kopā</b><span>Jūsu uzņēmuma kartīte Google meklētājā jau ir. Mājaslapas saiti var ielikt kartītē, lai cilvēks uzreiz redzētu jūsu pakalpojumus un cenas.</span></li>"
               if slug in HAS_CARD else
               "<li><b>Redzami arī kartē</b><span>Palīdzu izveidot vai sakārtot uzņēmuma kartīti internetā: jūsu adresi, darba laiku, tālruni un atsauksmes, ko cilvēki redz Google meklētājā un kartē.</span></li>")
    owner = "" if generic else f"""<section class="owner"><div class="wrap"><div class="card">
  <p class="tag">Tikai jums. Klienti šo daļu neredzēs.</p>
  <h2>Šo lapu sagatavoju tieši jums</h2>
  <p>Labdien! Mani sauc Raivo Harkovs, veidoju mājaslapas maziem uzņēmumiem. Šis ir paraugs, kā varētu izskatīties «{e(name)}» mājaslapa. Zemāk tā ir tāda, kādu to redzētu jūsu klients, jau ar jūsu nosaukumu un pakalpojumiem.</p>
  <ul>
    <li><b>Jūs atrod Google</b><span>Kad salūst auto, cilvēki meklē “{e(term)}”. Bez mājaslapas šie klienti aizbrauc pie tiem, kurus atrod. Lapā jūsu nosaukums, pilsēta un pakalpojumi ir norādīti arī meklētājam saprotamā veidā.</span></li>
    {CARD_LI}
    <li><b>Mazāk zvanu “cik maksā?”</b><span>Cenas un darba laiks ir redzami, tāpēc zvana tie, kas grib pieteikties.</span></li>
    <li><b>Pieteikumi arī vakaros</b><span>Forma strādā brīvdienās un pēc darba laika, kad telefonu neceļat.</span></li>
    <li><b>Jauni klienti uzticas ātrāk</b><span>Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.</span></li>
  </ul>
  <p class="next">Ja paraugs jums šķiet noderīgs, lūdzu, atbildiet uz manu e-pastu un norādiet, ko vēlaties mainīt. Paraugu pielāgošu jūsu uzņēmumam un publicēšu internetā kā gatavu mājaslapu. Šobrīd to daru bez maksas, lūdzot pretī tikai godīgu atsauksmi. Piedāvājums ir spēkā līdz 2026. gada beigām. Ja jums ir jautājumi par to, kā notiek sadarbība, labprāt jums piezvanīšu.</p>
  <p class="below">Jūsu lapas paraugs sākas šeit</p>
</div></div></section>
"""
    # structured data for search engines: business type, town and services
    ldd = {
        "@context": "https://schema.org", "@type": extra.get("ld", "AutoRepair"), "name": name,
        "address": {"@type": "PostalAddress", "addressLocality": town, "addressCountry": "LV"},
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": x}} for x in services],
    }
    page = (TPL
            .replace("{{THEME}}", "")
            .replace("{{ART}}", "" if L["design"] == "zimejums" else drawing)
            .replace("{{LOC}}", f" {e(loc)}" if loc else "")
            .replace("{{OWNER}}", owner)
            .replace("{{NAME}}", e(name))
            .replace("{{NOTE}}", note)
            .replace("{{EYEBROW}}", noun + (f" {e(loc)}" if loc else ""))
            .replace("{{H1}}", h1).replace("{{LEAD}}", lead).replace("{{PRICE_SUB}}", price_sub)
            .replace("{{EST}}", "".join(
                "        <tr%s><td>%s</td><td>%s €</td></tr>\n" % (' class="total"' if i == len(est) - 1 else "", a, b)
                for i, (a, b) in enumerate(est)))
            .replace("{{SEASON}}", "" if not season else
                     f'      <a class="notice" href="#pieteikums"><b>{season[0]}</b><span>{season[1]}</span><i>→</i></a>\n')
            .replace("{{PRICES}}", "".join(
                f'        <tr><td>{a}{f"<small>{n}</small>" if n else ""}</td><td>{p}</td></tr>\n' for a, n, p in prices))
            .replace("{{TOWN}}", e(town))
            .replace("{{INITIAL}}", e(name[0].upper()))
            .replace("{{SERVICES}}", "".join(card(s, prof, seen) for seen in [set()] for s in services)))
    for old, new in extra.get("swaps", []):
        assert old in page or (generic and "cilvēk" in old), (slug, old)
        page = page.replace(old, new)
    ph = var.get("ph") or PLACEHOLDER.get(prof)
    if ph:
        page = page.replace('placeholder="Piemēram, jumta maiņa, Cēsis"', f'placeholder="Piemēram, {ph}, {e(town) if loc else "Cēsis"}"')
    if "faq" in extra:
        page = re.sub(r"(    <details>.*</details>\n)+", "".join(
            f"    <details><summary>{q}</summary><p>{a}</p></details>\n" for q, a in extra["faq"]), page, count=1)
    if rest and rest[0] == "evak":
        page = page.replace("Pieteikt vizīti", "Izsaukt evakuatoru")
    # drop template habits that make pages look machine-made: section labels, tick rows, slogan triplets
    page = re.sub(r'\n *<p class="kicker">[^<]*</p>', "", page)
    page = re.sub(r'\n *<ul class="ticks">.*?</ul>', "", page, flags=re.S)
    page = re.sub(r'(<section class="why">.*?<h2[^>]*>)[^<]*(</h2>)', r"\1Kā strādājam\2", page, count=1, flags=re.S)
    page = page.replace('<input id="f-car"', '<input id="f-car" name="Papildu informācija"')
    page = apply_look(page, L, drawing, "../../../assets/foto/" if PREVIEW else "../assets/foto/")
    if not generic:  # a business demo does not link to the other samples
        page = page.replace(' <a href="../">Kas to veidoja un citi paraugi</a>', "").replace(' <a href="../">Par autoru un citi paraugi</a>', "")
    if slug in INFO:
        page = real_info(page, INFO[slug], ldd)
    hrs = INFO.get(slug, {}).get("hours")
    if hrs:
        ldd["openingHours"] = [f'{["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"][int(d)]} {v.replace(".", ":")}' for d, v in hrs.items()]
    page = page.replace("{{JSONLD}}", "" if generic else
                        '<script type="application/ld+json">' + json.dumps(ldd, ensure_ascii=False).replace("</", "<\\/") + "</script>\n")
    if LIVE:
        out = ROOT.parent / "klienti" / slug
        out.mkdir(parents=True, exist_ok=True)
        page, files = make_live(page, name, LIVECFG.get(slug, {}), out)
        for fn, body in files.items():
            (out / fn).write_text(body, encoding="utf-8")
    else:
        out = PRIV / "preview" / slug if PREVIEW else ROOT / slug
        out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("built", slug, "(live version in ../klienti)" if LIVE else "(preview only)" if PREVIEW else "")
