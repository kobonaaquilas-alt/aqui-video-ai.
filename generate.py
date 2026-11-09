import base64
import os
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests
from PIL import Image, UnidentifiedImageError
from gradio_client import Client

IMAGE_URL = os.environ["IMAGE_URL"].strip()
PROMPT = os.environ["PROMPT"].strip()
DURATION = int(float(os.environ.get("DURATION", "3")))
ALLOWED_DURATIONS = {2, 3, 4, 5, 6, 8, 10}
NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed, watermark, bad anatomy, static, shaky camera"

if DURATION not in ALLOWED_DURATIONS:
    raise SystemExit("Durée non autorisée. Choisis 2, 3, 4, 5, 6, 8 ou 10 secondes.")
if not IMAGE_URL.startswith(("https://", "http://")):
    raise SystemExit("IMAGE_URL doit être une URL HTTP(S) publique.")

parts = urlparse(IMAGE_URL)
if "dropbox.com" in parts.netloc:
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["dl"] = "1"
    query.pop("raw", None)
    IMAGE_URL = urlunparse(parts._replace(query=urlencode(query)))

print("Téléchargement de l'image source…")
response = requests.get(IMAGE_URL, headers={"User-Agent": "AQUI-VIDEO-AI/1.0"}, timeout=90, allow_redirects=True)
response.raise_for_status()
content_type = response.headers.get("Content-Type", "").lower()
if "text/html" in content_type or "application/json" in content_type:
    raise SystemExit("Le lien fourni renvoie une page web et non une image. Utilise un lien direct JPG/PNG/WEBP.")
if len(response.content) > 12 * 1024 * 1024:
    raise SystemExit("Image trop volumineuse (maximum 12 Mo).")

try:
    image = Image.open(BytesIO(response.content)).convert("RGB")
except (UnidentifiedImageError, OSError) as exc:
    raise SystemExit("Impossible de lire l'image. Vérifie que le lien est public et direct.") from exc

def image_to_data_url(source: Image.Image) -> str:
    source = source.copy()
    source.thumbnail((1280, 1280))
    buffer = BytesIO()
    source.save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

print("Connexion au Space Wan 2.2 public. Le démarrage GPU peut prendre du temps…")
client = Client("prithivMLmods/Wan2.2-Fast", verbose=True)
remaining = float(DURATION)
current_image = image_to_data_url(image)
segments = []
segment_number = 1

while remaining > 0:
    segment_duration = min(5.0, remaining)
    print(f"Génération du segment {segment_number} ({segment_duration:g} s)…")
    result = client.predict(
        current_image,
        PROMPT,
        4,
        NEGATIVE_PROMPT,
        segment_duration,
        1.0,
        1.0,
        42 + segment_number - 1,
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

    segment_path = Path(f"segment_{segment_number:02d}.mp4")
    segment_path.write_bytes(base64.b64decode(encoded))
    if segment_path.stat().st_size < 10_000:
        raise SystemExit("Le segment vidéo obtenu semble incomplet.")
    segments.append(segment_path)
    remaining -= segment_duration

    if remaining > 0:
        frame_path = Path(f"continuation_{segment_number:02d}.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(segment_path), "-frames:v", "1", str(frame_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if not frame_path.exists() or frame_path.stat().st_size < 1000:
            raise SystemExit("Impossible d'extraire l'image de continuité du segment précédent.")
        with Image.open(frame_path) as last_frame:
            current_image = image_to_data_url(last_frame.convert("RGB"))
    segment_number += 1

output = Path("output.mp4")
if len(segments) == 1:
    output.write_bytes(segments[0].read_bytes())
else:
    concat_file = Path("segments.txt")
    concat_file.write_text("".join(f"file '{segment.resolve()}'\n" for segment in segments), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "16", "-movflags", "+faststart", str(output),
        ],
        check=True,
    )

if output.stat().st_size < 10_000:
    raise SystemExit("Le fichier MP4 final semble incomplet.")
print(f"Vidéo créée : {output} ({output.stat().st_size} octets), durée demandée : {DURATION} s")
