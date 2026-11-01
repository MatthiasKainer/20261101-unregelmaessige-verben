"""Download SIL Open Font License fonts on GitHub Actions runners."""
from pathlib import Path
import urllib.request

TARGET = Path(__file__).resolve().parents[1] / "assets" / "fonts"
# Static faces are vendored in assets/fonts (OFL). Download only if missing.
ASSETS = {
    "RussoOne-Regular.ttf": "ofl/russoone/RussoOne-Regular.ttf",
    "ChakraPetch-SemiBold.ttf": "ofl/chakrapetch/ChakraPetch-SemiBold.ttf",
    "ChakraPetch-Bold.ttf": "ofl/chakrapetch/ChakraPetch-Bold.ttf",
    "ChakraPetch-Regular.ttf": "ofl/chakrapetch/ChakraPetch-Regular.ttf",
    "Orbitron-Regular.ttf": "ofl/orbitron/Orbitron%5Bwght%5D.ttf",
}
VENDORED = (
    "RussoOne-Regular.ttf",
    "ChakraPetch-SemiBold.ttf",
    "ChakraPetch-Bold.ttf",
    "Orbitron-Black.ttf",
)

def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    if all((TARGET / name).is_file() and (TARGET / name).stat().st_size > 8000 for name in VENDORED):
        print("fonts already vendored")
        return
    for name, asset in ASSETS.items():
        data = urllib.request.urlopen(
            "https://raw.githubusercontent.com/google/fonts/main/" + asset, timeout=20
        ).read()
        assert len(data) > 10000 and data[:4] in (b"\x00\x01\x00\x00", b"OTTO"), name
        (TARGET / name).write_bytes(data)
        print("validated font:", name, len(data))
        family = asset.split("/")[1]
        license_data = urllib.request.urlopen(
            "https://raw.githubusercontent.com/google/fonts/main/ofl/" + family + "/OFL.txt", timeout=20
        ).read()
        assert b"SIL OPEN FONT LICENSE" in license_data.upper()
        (TARGET / (family + "-OFL.txt")).write_bytes(license_data)

if __name__ == "__main__":
    main()
