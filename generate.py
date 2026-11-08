import base64
import os
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from gradio_client import Client

IMAGE_URL = os.environ["IMAGE_URL"].strip()
PROMPT = os.environ["PROMPT"].strip()
DURATION = float(os.environ.get("DURATION", "3"))

if not IMAGE_URL.startswith(("https://", "http://")):
    raise SystemExit("IMAGE_URL doit être une URL HTTP(S) publique.")

print("Téléchargement de l'image source…")
response = requests.get(IMAGE_URL, timeout=60)
response.raise_for_status()
if len(response.content) > 12 * 1024 * 1024:
    raise SystemExit("Image trop volumineuse (maximum 12 Mo).")

image = Image.open(BytesIO(response.content)).convert("RGB")
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
