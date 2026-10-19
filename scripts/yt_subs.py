from youtube_transcript_api import YouTubeTranscriptApi

try:
    with open("yt_video_id.txt", "r") as f:
        video_id = f.read().strip()
    if not video_id:
        print("yt_video_id.txt is empty. Please upload a video first.")
        exit(1)
except FileNotFoundError:
    print("yt_video_id.txt not found. Please upload a video first.")
    exit(1)

try:
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id, languages=["el", "en"])
    with open("yt_transcript.txt", "w", encoding="utf-8") as f:
        for entry in transcript:
            f.write(entry.text + "\n")
except Exception as e:
    print(f"Error fetching transcript: {e}")
    exit(1)


# there is no need for authentication since the videos are now "unlisted"