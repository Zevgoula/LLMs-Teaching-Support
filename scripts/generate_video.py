# wav audio (lecture recording) to video (mp4) with a static image
import os

# wav audio (lecture recording) to video (mp4) with a static image
import os
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent)) # to import config

from config import USER_FILES_DIR

def wav_to_mp4(audio_path, image_path, output_path=None):
    audio_path = Path(audio_path)
    if output_path is None:
        output_path = USER_FILES_DIR / "video" / (audio_path.stem + ".mp4")
    print(f"Output path: {output_path}")

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "1", "-i", image_path,  # repeat the image as video
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-crf", "40", "-pix_fmt", "yuv420p",
        "-vf", "scale=320:180:force_original_aspect_ratio=decrease,"
               "pad=320:180:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path

if __name__ == "__main__":
   wav_to_mp4(USER_FILES_DIR / "audio" / "avouris.wav", "cover.png")