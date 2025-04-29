import os
import threading
import subprocess
import time

# Parameters
chunk_dir = 'recordings'
merged_output = 'final_output.mp4'
file_format = '.mp4'
chunk_duration = 10          # seconds
max_chunks =     6         # Max chunks to keep
fps = 30
resolution = '640x480'

# Ensure chunk directory exists
os.makedirs(chunk_dir, exist_ok=True)

def is_valid_video(file_path):
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1',
            file_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False


def merge_chunks():
    """Merge chunks using a temp list. Only validate the newest one."""

    if not merge_lock.acquire(blocking=False):
        print("⏳ Merge already in progress. Skipping this call.")
        return

    start_time = time.time()
    print("🧩 Merging chunks...")

    list_path = None  # Prevent UnboundLocalError if early return

    try:
        all_files = sorted([
            f for f in os.listdir(chunk_dir)
            if f.endswith(file_format)
        ])

        if len(all_files) < 2:
            print("⚠️ Not enough chunks to merge.")
            return

        # Validate only the second-last chunk (last completed one)
        newest_file = all_files[-2]
        newest_path = os.path.abspath(os.path.join(chunk_dir, newest_file))

        if not is_valid_video(newest_path):
            print(f"🚫 Invalid chunk detected and removed: {newest_file}")
            os.remove(newest_path)
            all_files.pop(-2)  # Remove the bad chunk from the list
            if len(all_files) < 2:
                print("⚠️ Not enough valid chunks to merge after removal.")
                return


        completed_files = all_files[:-1]
        chunk_paths = [
            os.path.abspath(os.path.join(chunk_dir, f))
            for f in completed_files
        ]

        # Create temporary chunk list file
        list_path = os.path.join(chunk_dir, 'chunks_tmp.txt')
        with open(list_path, 'w') as f:
            for path in chunk_paths:
                f.write(f"file '{path}'\n")

        # Remove old merged file if it exists
        if os.path.exists(merged_output):
            os.remove(merged_output)
            print(f"🗑️ Deleted previous output file: {merged_output}")

        # Run FFmpeg merge
        subprocess.run([
            'ffmpeg', '-loglevel', 'error',
            '-y', '-f', 'concat', '-safe', '0', '-i',
            list_path,
            '-c', 'copy',
            merged_output
        ], check=True)

        print(f"🎞️ Final merged video updated with {len(chunk_paths)} chunks.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to merge: {e}")

    finally:
        if list_path is not None and os.path.exists(list_path):
            os.remove(list_path)
        merge_lock.release()
        elapsed_time = time.time() - start_time
        print(f"⏱️ Time taken : {elapsed_time:.2f} seconds")


def rotate_files():
    """Keep only the newest max_chunks"""
    files = sorted([f for f in os.listdir(chunk_dir) if f.endswith(file_format)])
    if len(files) > max_chunks:
        to_delete = files[:len(files) - max_chunks]
        for fname in to_delete:
            os.remove(os.path.join(chunk_dir, fname))
            print(f"🗑️ Deleted old chunk: {fname}")

# Background merge thread function
merge_event = threading.Event()
merge_lock = threading.Lock()

def merge_worker():
    while True:
        merge_event.wait()
        merge_event.clear()
        merge_chunks()

# Start FFmpeg recording with segmentation
def start_segmented_recording():
    output_template = os.path.join(chunk_dir, f"%Y%m%d_%H%M%S{file_format}")

    ffmpeg_command = [
        'ffmpeg',
        '-loglevel', 'error',
        '-f', 'v4l2',
        '-framerate', str(fps),
        '-video_size', resolution,
        '-i', '/dev/video0',
        '-f', 'alsa',
        '-i', 'plughw:1,0',  # Replace with your microphone device
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-g', str(fps),
        '-keyint_min', str(fps),
        '-sc_threshold', '0',
        '-vf', (
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "text='%{localtime\\:%m-%d-%y %H\\\\\\:%M\\\\\\:%S}':"
            "x=10:y=10:fontsize=16:fontcolor=white:"
            "box=1:boxcolor=black@0.3:boxborderw=5"
        ),
        '-c:a', 'aac',
        '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-f', 'segment',
        '-segment_time', str(chunk_duration),
        '-segment_clocktime_offset', '0',
        '-reset_timestamps', '1',
        '-strftime', '1',
        output_template
    ]

    return subprocess.Popen(ffmpeg_command)

# --- MAIN ---
try:
    # Start merge thread
    threading.Thread(target=merge_worker, daemon=True).start()

    # Start FFmpeg segmented recording
    recording_process = start_segmented_recording()
    print("🎥 Continuous recording started...")

    while True:
        time.sleep(chunk_duration + 1)
        rotate_files()
        if not merge_lock.locked():
            merge_event.set()
        else:
            print("⏳ Merge in progress — skipping this round")

except KeyboardInterrupt:
    print("🛑 Stopping recording...")
    if recording_process:
        recording_process.terminate()
        recording_process.wait()
    print("👋 Goodbye!")
