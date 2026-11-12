"""Regenerates the portfolio preview images from the generic demos. Run after design changes:
    python _src/screenshots.py
Needs Google Chrome and Pillow (pip install pillow)."""
import pathlib, subprocess, tempfile
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BANNER = 42  # the yellow "this is a sample" bar at the top of every demo, cropped out of previews
DEMOS = {"auto": "autoserviss", "buve": "buvfirma", "ziedi": "ziedu-salons", "kafe": "kafejnica",
         "zobi": "zobarstnieciba", "friz": "frizetava", "vet": "veterinara-klinika", "beres": "apbedisanas-birojs"}


def shot(slug, w, h, scale=1):
    out = pathlib.Path(tempfile.gettempdir()) / f"shot-{slug}-{w}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                    f"--window-size={w},{h + BANNER}", "--virtual-time-budget=9000", f"--screenshot={out}",
                    (ROOT / slug / "index.html").as_uri() + "?still"],  # ?still shows the page with its animations finished
                   check=True, capture_output=True)
    im = Image.open(out).convert("RGB")
    return im.crop((0, BANNER * scale, w * scale, (h + BANNER) * scale))


for key, slug in DEMOS.items():
    im = shot(slug, 1280, 2560).resize((900, 1800), Image.LANCZOS)
    im.save(ROOT / "assets" / f"paraugs-{key}.jpg", quality=72, optimize=True, progressive=True)
    if key == "auto":  # social share image
        shot(slug, 1280, 672).resize((1200, 630), Image.LANCZOS).save(ROOT / "assets" / "paraugs.jpg", quality=80, optimize=True)
    print("saved", key)
shot("autoserviss", 390, 844, 2).resize((390, 844), Image.LANCZOS).save(ROOT / "assets" / "paraugs-telefona.jpg", quality=78, optimize=True)
print("saved phone")
