# import subprocess

# try:
#     subprocess.run([
#         'ffmpeg',
#         '-f', 'v4l2',
#         '-input_format', 'yuyv422',
#         '-framerate', '30',
#         '-video_size', '640x480',
#         '-i', '/dev/video0',
#         '-f', 'alsa',
#         '-ac', '1',
#         '-ar', '44100',
#         '-i', 'plughw:1,0',  # <<<<<< changed here
#         '-c:v', 'libx264',
#         '-preset', 'ultrafast',
#         '-c:a', 'aac',
#         '-b:a', '128k',
#         '-pix_fmt', 'yuv420p',
#         '-shortest',
#         'output.mp4'
#     ], check=True)
#     print("✅ Recording finished. Saved to output.mp4")

# except subprocess.CalledProcessError as e:
#     print(f"❌ An error occurred while recording: {e}")

# import os
# import subprocess
# import threading
# import time
# import glob
# import signal

# # Parameters
# chunk_dir = 'recordings'
# merged_output = 'final_output.mp4'
# file_format = '.mp4'
# chunk_duration = 10    # seconds
# max_chunks = 6         # How many chunks to keep (example: 6 chunks = last 60 seconds)
# fps = 30
# resolution = '640x480'

# # Ensure chunk directory exists
# os.makedirs(chunk_dir, exist_ok=True)

# def delete_old_chunks():
#     """Delete old chunks if exceeding max_chunks"""
#     files = sorted(glob.glob(os.path.join(chunk_dir, f'*{file_format}')))
#     if len(files) > max_chunks:
#         files_to_delete = files[:len(files) - max_chunks]
#         for f in files_to_delete:
#             os.remove(f)
#             print(f"🗑️ Deleted old chunk: {os.path.basename(f)}")

# def merge_chunks():
#     """Merge completed chunks into one output video"""
#     print("🧩 Merging chunks...")

#     all_files = sorted(glob.glob(os.path.join(chunk_dir, f'*{file_format}')))
#     if not all_files:
#         print("⚠️ No chunks to merge.")
#         return

#     # Exclude the newest file (which is still being written)
#     completed_files = all_files[:-1]

#     if not completed_files:
#         print("⚠️ No completed chunks to merge yet.")
#         return

#     list_path = os.path.join(chunk_dir, 'chunks.txt')
#     with open(list_path, 'w') as f:
#         for filepath in completed_files:
#             f.write(f"file '{os.path.abspath(filepath)}'\n")

#     try:
#         subprocess.run([
#             'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i',
#             list_path, '-c', 'copy', merged_output
#         ], check=True)
#         print(f"✅ Final merged video saved to: {merged_output}")
#     except subprocess.CalledProcessError as e:
#         print(f"❌ Failed to merge chunks: {e}")
#     finally:
#         if os.path.exists(list_path):
#             os.remove(list_path)


# def start_ffmpeg_segment_recording():
#     """Start ffmpeg continuous recording with auto splitting"""
#     ffmpeg_command = [
#         'ffmpeg',
#         '-f', 'v4l2',
#         '-framerate', str(fps),
#         '-video_size', resolution,
#         '-i', '/dev/video0',
#         '-f', 'alsa',
#         '-i', 'plughw:1,0',
#         '-c:v', 'libx264',
#         '-preset', 'ultrafast',
#         '-c:a', 'aac',
#         '-b:a', '128k',
#         '-pix_fmt', 'yuv420p',
#         '-f', 'segment',
#         '-segment_time', str(chunk_duration),
#         '-reset_timestamps', '1',
#         '-strftime', '1',
#         os.path.join(chunk_dir, '%Y%m%d_%H%M%S' + file_format)
#     ]

#     process = subprocess.Popen(ffmpeg_command)
#     return process

# def monitor_chunks():
#     """Continuously monitor folder to delete old chunks"""
#     while True:
#         delete_old_chunks()
#         time.sleep(5)  # Check every 5 seconds

# # Main
# if __name__ == "__main__":
#     try:
#         print("🎥 Starting continuous recording...")
#         recorder = start_ffmpeg_segment_recording()

#         # Start chunk monitor in background
#         monitor_thread = threading.Thread(target=monitor_chunks, daemon=True)
#         monitor_thread.start()

#         # Wait for user to stop (Ctrl+C)
#         while True:
#             time.sleep(1)

#     except KeyboardInterrupt:
#         print("🛑 Stopping recording...")
#         recorder.send_signal(signal.SIGINT)
#         recorder.wait()
#         print("📦 Recording stopped. Merging final video...")

#         merge_chunks()
#         print("👋 Goodbye!")

import os
import threading
import subprocess
import time

# Parameters
chunk_dir = 'recordings'
merged_output = 'final_output.mp4'
file_format = '.mp4'
chunk_duration = 10          # seconds
max_chunks = 4               # Max chunks to keep
fps = 30
resolution = '640x480'

# Ensure chunk directory exists
os.makedirs(chunk_dir, exist_ok=True)

def merge_chunks():
    """Merge completed chunks into one output video"""
    print("🧩 Merging chunks...")

    all_files = sorted([f for f in os.listdir(chunk_dir) if f.endswith(file_format)])
    if not all_files:
        print("⚠️ No chunks to merge.")
        return

    # Skip the newest file (still recording)
    completed_files = all_files[:-1]

    if not completed_files:
        print("⚠️ No completed chunks to merge yet.")
        return

    list_path = os.path.join(chunk_dir, 'chunks.txt')
    with open(list_path, 'w') as f:
        for filename in completed_files:
            f.write(f"file '{os.path.abspath(os.path.join(chunk_dir, filename))}'\n")

    try:
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i',
            list_path, '-c', 'copy', merged_output
        ], check=True)
        print(f"✅ Final merged video saved to: {merged_output}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to merge chunks: {e}")
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)

def rotate_files():
    """Keep only the newest max_chunks"""
    files = sorted([f for f in os.listdir(chunk_dir) if f.endswith(file_format)])
    if len(files) > max_chunks:
        to_delete = files[:len(files) - max_chunks]
        for fname in to_delete:
            os.remove(os.path.join(chunk_dir, fname))
            print(f"🗑️ Deleted old chunk: {fname}")

# Start FFmpeg recording with segmentation
def start_segmented_recording():
    output_template = os.path.join(chunk_dir, f"%Y%m%d_%H%M%S{file_format}")

    ffmpeg_command = [
        'ffmpeg',
        '-f', 'v4l2',
        '-framerate', str(fps),
        '-video_size', resolution,
        '-i', '/dev/video0',
        '-f', 'alsa',
        '-i', 'plughw:1,0',   # your microphone device
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',            # << added CRF for quality/size balance
        '-g', str(fps),        # <<< ADD THIS: keyframe every 1 second (30 frames)
        '-keyint_min', str(fps),  # <<< Also minimum keyframe distance
        '-sc_threshold', '0',     # <<< Disable scene-cut based keyframes (optional, makes cuts predictable)
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
    recording_process = start_segmented_recording()
    print("🎥 Continuous recording started...")

    while True:
        time.sleep(chunk_duration + 1)

        rotate_files()

        # Merge in background
        merge_thread = threading.Thread(target=merge_chunks)
        merge_thread.start()

except KeyboardInterrupt:
    print("🛑 Stopping recording...")
    if recording_process:
        recording_process.terminate()
        recording_process.wait()
    print("👋 Goodbye!")


# import subprocess

# try:
#     subprocess.run([
#         'ffmpeg',
#         '-f', 'v4l2',
#         '-input_format', 'yuyv422',
#         '-framerate', '30',
#         '-video_size', '640x480',
#         '-i', '/dev/video0',
#         '-f', 'alsa',
#         '-ac', '1',
#         '-ar', '44100',
#         '-i', 'plughw:1,0',  # <<<<<< changed here
#         '-c:v', 'libx264',
#         '-preset', 'ultrafast',
#         '-c:a', 'aac',
#         '-b:a', '128k',
#         '-pix_fmt', 'yuv420p',
#         '-shortest',
#         'output.mp4'
#     ], check=True)
#     print("✅ Recording finished. Saved to output.mp4")

# except subprocess.CalledProcessError as e:
#     print(f"❌ An error occurred while recording: {e}")

# import os
# import subprocess
# import threading
# import time
# import glob
# import signal

# # Parameters
# chunk_dir = 'recordings'
# merged_output = 'final_output.mp4'
# file_format = '.mp4'
# chunk_duration = 10    # seconds
# max_chunks = 6         # How many chunks to keep (example: 6 chunks = last 60 seconds)
# fps = 30
# resolution = '640x480'

# # Ensure chunk directory exists
# os.makedirs(chunk_dir, exist_ok=True)

# def delete_old_chunks():
#     """Delete old chunks if exceeding max_chunks"""
#     files = sorted(glob.glob(os.path.join(chunk_dir, f'*{file_format}')))
#     if len(files) > max_chunks:
#         files_to_delete = files[:len(files) - max_chunks]
#         for f in files_to_delete:
#             os.remove(f)
#             print(f"🗑️ Deleted old chunk: {os.path.basename(f)}")

# def merge_chunks():
#     """Merge completed chunks into one output video"""
#     print("🧩 Merging chunks...")

#     all_files = sorted(glob.glob(os.path.join(chunk_dir, f'*{file_format}')))
#     if not all_files:
#         print("⚠️ No chunks to merge.")
#         return

#     # Exclude the newest file (which is still being written)
#     completed_files = all_files[:-1]

#     if not completed_files:
#         print("⚠️ No completed chunks to merge yet.")
#         return

#     list_path = os.path.join(chunk_dir, 'chunks.txt')
#     with open(list_path, 'w') as f:
#         for filepath in completed_files:
#             f.write(f"file '{os.path.abspath(filepath)}'\n")

#     try:
#         subprocess.run([
#             'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i',
#             list_path, '-c', 'copy', merged_output
#         ], check=True)
#         print(f"✅ Final merged video saved to: {merged_output}")
#     except subprocess.CalledProcessError as e:
#         print(f"❌ Failed to merge chunks: {e}")
#     finally:
#         if os.path.exists(list_path):
#             os.remove(list_path)


# def start_ffmpeg_segment_recording():
#     """Start ffmpeg continuous recording with auto splitting"""
#     ffmpeg_command = [
#         'ffmpeg',
#         '-f', 'v4l2',
#         '-framerate', str(fps),
#         '-video_size', resolution,
#         '-i', '/dev/video0',
#         '-f', 'alsa',
#         '-i', 'plughw:1,0',
#         '-c:v', 'libx264',
#         '-preset', 'ultrafast',
#         '-c:a', 'aac',
#         '-b:a', '128k',
#         '-pix_fmt', 'yuv420p',
#         '-f', 'segment',
#         '-segment_time', str(chunk_duration),
#         '-reset_timestamps', '1',
#         '-strftime', '1',
#         os.path.join(chunk_dir, '%Y%m%d_%H%M%S' + file_format)
#     ]

#     process = subprocess.Popen(ffmpeg_command)
#     return process

# def monitor_chunks():
#     """Continuously monitor folder to delete old chunks"""
#     while True:
#         delete_old_chunks()
#         time.sleep(5)  # Check every 5 seconds

# # Main
# if __name__ == "__main__":
#     try:
#         print("🎥 Starting continuous recording...")
#         recorder = start_ffmpeg_segment_recording()

#         # Start chunk monitor in background
#         monitor_thread = threading.Thread(target=monitor_chunks, daemon=True)
#         monitor_thread.start()

#         # Wait for user to stop (Ctrl+C)
#         while True:
#             time.sleep(1)

#     except KeyboardInterrupt:
#         print("🛑 Stopping recording...")
#         recorder.send_signal(signal.SIGINT)
#         recorder.wait()
#         print("📦 Recording stopped. Merging final video...")

#         merge_chunks()
#         print("👋 Goodbye!")

# import os
# import threading
# import subprocess
# import time

# # Parameters
# chunk_dir = 'recordings'
# merged_output = 'final_output.mp4'
# file_format = '.mp4'
# chunk_duration = 10          # seconds
# max_chunks = 720               # Max chunks to keep
# fps = 30
# resolution = '640x480'


# def is_valid_video(file_path):
#     """Return True if FFmpeg can read the video file without error."""
#     try:
#         result = subprocess.run([
#             'ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-'
#         ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
#         return result.returncode == 0
#     except Exception:
#         return False
# # Ensure chunk directory exists
# os.makedirs(chunk_dir, exist_ok=True)

# def merge_chunks():
#     """Merge only valid completed chunks into one output video."""
#     print("🧩 Merging chunks...")

#     all_files = sorted([
#         f for f in os.listdir(chunk_dir)
#         if f.endswith(file_format)
#     ])

#     if not all_files:
#         print("⚠️ No chunks to merge.")
#         return

#     completed_files = all_files[:-1]  # Exclude the most recent (still recording)

#     valid_paths = []
#     for filename in completed_files:
#         full_path = os.path.abspath(os.path.join(chunk_dir, filename))
#         if os.path.exists(full_path) and is_valid_video(full_path):
#             valid_paths.append(full_path)
#         else:
#             print(f"🚫 Skipping unreadable or corrupt file: {filename}")

#     if not valid_paths:
#         print("❌ No valid chunks to merge.")
#         return

#     list_path = os.path.join(chunk_dir, 'chunks.txt')
#     with open(list_path, 'w') as f:
#         for path in valid_paths:
#             f.write(f"file '{path}'\n")

#     try:
#          # Delete existing output file if it exists
#         if os.path.exists(merged_output):
#             os.remove(merged_output)
#             print(f"🗑️ Deleted previous output file: {merged_output}",flush=True)
#         else:
#             print("📂 No previous output file to delete.")

#         subprocess.run([
#             'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i',
#             list_path, '-c', 'copy', merged_output
#         ], check=True)
#         print(f"✅ Final merged video saved to: {merged_output}")
#     except subprocess.CalledProcessError as e:
#         print(f"❌ Failed to merge chunks: {e}")
#     finally:
#         if os.path.exists(list_path):
#             os.remove(list_path)

# def rotate_files():
#     """Keep only the newest max_chunks"""
#     files = sorted([f for f in os.listdir(chunk_dir) if f.endswith(file_format)])
#     if len(files) > max_chunks:
#         to_delete = files[:len(files) - max_chunks]
#         for fname in to_delete:
#             os.remove(os.path.join(chunk_dir, fname))
#             print(f"🗑️ Deleted old chunk: {fname}")

# # Start FFmpeg recording with segmentation
# def start_segmented_recording():
#     output_template = os.path.join(chunk_dir, f"%Y%m%d_%H%M%S{file_format}")

#     ffmpeg_command = [
#         'ffmpeg',
#          '-loglevel', 'quiet',       # <--- stop log
#         '-f', 'v4l2',
#         '-framerate', str(fps),
#         '-video_size', resolution,
#         '-i', '/dev/video0',
#         '-f', 'alsa',
#         '-i', 'plughw:2,0',   # your microphone device
#         '-c:v', 'libx264',
#         '-preset', 'veryfast',  # Fast encoding preset for compact size
#         #'-preset', 'ultrafast',
#         '-crf', '23',            # << added CRF for quality/size balance or compact size
#         '-g', str(fps),        # <<< ADD THIS: keyframe every 1 second (30 frames)
#         '-keyint_min', str(fps),  # <<< Also minimum keyframe distance
#         '-sc_threshold', '0',     # <<< Disable scene-cut based keyframes (optional, makes cuts predictable)
        
#         # Add drawtext filter
#         '-vf', (
#             "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
#             "text='%{localtime\\:%m-%d-%y %H\\\\\\:%M\\\\\\:%S}':"
#             "x=10:y=10:fontsize=16:fontcolor=white:"
#             "box=1:boxcolor=black@0.3:boxborderw=5"
#         ),

#         '-c:a', 'aac',
#         '-b:a', '128k',
#         '-pix_fmt', 'yuv420p',
#         '-f', 'segment',
#         '-segment_time', str(chunk_duration),
#         '-segment_clocktime_offset', '0',
#         '-reset_timestamps', '1',
#         '-strftime', '1',
#         output_template
#     ]

#     return subprocess.Popen(ffmpeg_command)
# # --- MAIN ---

# try:
#     recording_process = start_segmented_recording()
#     print("🎥 Continuous recording started...")

#     while True:
#         time.sleep(chunk_duration + 1)

#         rotate_files()

#         # Merge in background
#         merge_thread = threading.Thread(target=merge_chunks)
#         merge_thread.start()
#         # merge_thread.join()  # Wait for merge to finish before next loop

# except KeyboardInterrupt:
#     print("🛑 Stopping recording...")
#     if recording_process:
#         recording_process.terminate()
#         recording_process.wait()
#     print("👋 Goodbye!")

    ################################################