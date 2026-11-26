from youtube_transcript_api import YouTubeTranscriptApi

try:
    with open("yt_video_id.txt", "r") as f:
        video_id = "xTrJMV2LC3I"
    if not video_id:
        print("yt_video_id.txt is empty. Please upload a video first.")
        exit(1)
except FileNotFoundError:
    print("yt_video_id.txt not found. Please upload a video first.")
    exit(1)

try:
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id, languages=["el"])
    with open("yt_transcript.txt", "w", encoding="utf-8") as f:
        for entry in transcript:
            f.write(entry.text + "\n")
    print(f"Transcript saved to yt_transcript.txt")
except Exception as e:
    print(f"Error fetching transcript: {e}") 
    exit(1)


# there is no need for authentication since the videos are now "unlisted"/"public"