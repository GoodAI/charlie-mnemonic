import subprocess
import json

def print_video_details(file_path):
    #command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
    #ffmpeg -i input.mp4 -vcodec h264 output.mp4
    command = ["ffmpeg", "-i", file_path, "-vcodec", "h264", "static/data/output.mp4"]
    output = subprocess.check_output(command).decode("utf-8")
    video_details = json.loads(output)

    print(json.dumps(video_details, indent=4))

print_video_details("static/data/countdown.mp4")