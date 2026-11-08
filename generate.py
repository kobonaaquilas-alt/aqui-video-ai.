import base64
import os
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests
from PIL import Image, UnidentifiedImageError
from gradio_client import Client

IMAGE_URL = os.environ["IMAGE_URL"].strip()
PROMPT = os.environ["PROMPT"].strip()
DURATION = float(os.environ.get("DURATION", "3"))

if not IMAGE_URL.startswith(("https://", "http://")):
    raise SystemExit("IMAGE_URL doit être une URL HTTP(S) publique.")

# Convert Dropbox share links into direct-download links.
parts = urlparse(IMAGE_URL)
if "dropbox.com" in parts.netloc:
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["dl"] = "1"
    query.pop("raw", None)
    IMAGE_URL = urlunparse(parts._replace(query=urlencode(query)))

print("Téléchargement de l'image source…")
response = requests.get(
    IMAGE_URL,
    headers={"User-Agent": "AQUI-VIDEO-AI/1.0"},
    timeout=90,
    allow_redirects=True,
)
response.raise_for_status()

content_type = response.headers.get("Content-Type", "").lower()
if "text/html" in content_type or "application/json" in content_type:
    raise SystemExit(
        "Le lien fourni renvoie une page web et non une image. "
        "Utilise un lien public direct JPG/PNG/WEBP (Dropbox avec dl=1)."
    )
if len(response.content) > 12 * 1024 * 1024:
    raise SystemExit("Image trop volumineuse (maximum 12 Mo).")

try:
    image = Image.open(BytesIO(response.content)).convert("RGB")
except (UnidentifiedImageError, OSError) as exc:
    raise SystemExit(
        "Impossible de lire l'image. Vérifie que le lien est public "
        "et pointe directement vers un fichier image."
    ) from exc

image.thumbnail((1280, 1280))
buffer = BytesIO()
image.save(buffer, format="JPEG", quality=88)
image_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

print("Connexion au Space Wan 2.2 public. Le démarrage GPU peut prendre du temps…")
client = Client("prithivMLmods/Wan2.2-Fast", verbose=True)
result = client.predict(
    image_b64,
    PROMPT,
    4,
    "blurry, low quality, distorted, deformed, watermark, bad anatomy, static, shaky camera",
    DURATION,
    1.0,
    1.0,
    42,
    True,
    api_name="/generate_video",
)

if not isinstance(result, dict) or "video" not in result:
    raise SystemExit(f"Réponse inattendue du Space : {type(result).__name__}")

video_data = result["video"]
if not isinstance(video_data, str) or "," not in video_data:
    raise SystemExit("Le Space n'a pas renvoyé de vidéo encodée.")

header, encoded = video_data.split(",", 1)
if "video/mp4" not in header:
    raise SystemExit(f"Format vidéo inattendu : {header}")

output = Path("output.mp4")
output.write_bytes(base64.b64decode(encoded))
if output.stat().st_size < 10_000:
    raise SystemExit("Le fichier vidéo obtenu semble incomplet.")

print(f"Vidéo créée : {output} ({output.stat().st_size} octets)")
