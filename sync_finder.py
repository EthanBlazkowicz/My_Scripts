import subprocess
import os
import argparse
import re
import numpy as np
import scipy.signal

def extract_audio_chunk(file_path, duration=60, sample_rate=16000):
    """
    Extracts the first N seconds of audio using FFmpeg via stdout.
    This prevents downloading or reading the whole file across the Samba share.
    """
    print(f"Streaming initial audio from: {os.path.basename(file_path)}...")
    
    command = [
        'ffmpeg',
        '-ss', '0',               # Start at the absolute beginning
        '-i', file_path,          # Input path (Samba mount)
        '-t', str(duration),      # Stop reading after N seconds
        '-vn',                    # Drop the video track completely
        '-ac', '1',               # Convert to Mono
        '-ar', str(sample_rate),  # Downsample to 16kHz for fast processing
        '-f', 's16le',            # Output raw 16-bit PCM audio
        '-'                       # Pipe directly to stdout (RAM memory)
    ]
    
    # Execute FFmpeg without writing temporary files to your drive
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed reading {os.path.basename(file_path)}.\nError: {stderr.decode('utf-8', errors='ignore')}")
        
    # Convert raw binary PCM bytes into a numerical array
    return np.frombuffer(stdout, dtype=np.int16)

def calculate_offset(file_bluray, file_streaming, duration=60, sample_rate=16000, output_txt="sync_offset_results.txt", append_mode=False):
    try:
        # Extract the audio arrays
        audio_br = extract_audio_chunk(file_bluray, duration, sample_rate)
        audio_str = extract_audio_chunk(file_streaming, duration, sample_rate)
        
        print("Analyzing audio timelines (cross-correlating wave patterns)...")
        
        # Center the signals around zero to prevent volume imbalances from breaking the match
        audio_br_norm = audio_br.astype(np.float32) - np.mean(audio_br)
        audio_str_norm = audio_str.astype(np.float32) - np.mean(audio_str)
        
        # Slide the streaming waveform against the Blu-ray waveform to find the perfect overlap
        correlation = scipy.signal.correlate(audio_br_norm, audio_str_norm, mode='full')
        lags = scipy.signal.correlation_lags(len(audio_br_norm), len(audio_str_norm), mode='full')
        
        # Find the peak correlation index
        best_lag = lags[np.argmax(correlation)]
        offset_seconds = best_lag / sample_rate
        
        # Construct the final report
        report = (
            f"=== TIMELINE SYNC REPORT ===\n"
            f"Reference (Blu-ray): {file_bluray}\n"
            f"Target (Streaming):  {file_streaming}\n"
            f"----------------------------------------\n"
            f"Exact Offset: {offset_seconds:.3f} seconds\n\n"
        )
        
        if offset_seconds > 0:
            report += f"Result: The Blu-ray version is DELAYED by {abs(offset_seconds):.3f}s relative to the streaming version.\n"
            report += f"Action: Delay your streaming subtitles by +{abs(offset_seconds):.3f}s to match the Blu-ray frame timing.\n"
        elif offset_seconds < 0:
            report += f"Result: The Streaming version is DELAYED by {abs(offset_seconds):.3f}s relative to the Blu-ray version.\n"
            report += f"Action: Accelerate your streaming subtitles by -{abs(offset_seconds):.3f}s to match the Blu-ray frame timing.\n"
        else:
            report += "Result: Both files are perfectly aligned down to the millisecond!\n"
            
        print(f"\n{report}")
        
        # Save results to text file
        mode = "a" if append_mode else "w"
        with open(output_txt, mode, encoding="utf-8") as f:
            f.write(f"{offset_seconds:.3f}\n")
        print(f"Results successfully compiled to: {os.path.abspath(output_txt)}")
        
    except Exception as e:
        error_msg = f"Sync analysis failed for {os.path.basename(file_streaming)}: {str(e)}"
        print(error_msg)
        mode = "a" if append_mode else "w"
        with open(output_txt, mode, encoding="utf-8") as f:
            f.write("0.000\n")

def get_episode_key(filename):
    """
    Extracts an episode identifier token (e.g., 's01e01', '1x02', or standalone ep numbers)
    to map files across folders accurately.
    """
    # Matches common tags like S01E01 or 1x01
    match = re.search(r'[sS]\d+[eE]\d+|\d+x\d+', filename)
    if match:
        return match.group(0).lower()
    
    # Fallback: find standalone numbers, skipping common video resolutions
    numbers = re.findall(r'\b\d{1,2}\b', filename)
    numbers = [n for n in numbers if n not in ['720', '1080', '2160']]
    if numbers:
        return f"ep{int(numbers[0]):02d}"
    return None

def match_directories(bluray_dir, streaming_dir):
    """Scans directories and pairs corresponding files together based on episode keys."""
    br_files = [f for f in os.listdir(bluray_dir) if os.path.isfile(os.path.join(bluray_dir, f))]
    str_files = [f for f in os.listdir(streaming_dir) if os.path.isfile(os.path.join(streaming_dir, f))]
    
    br_map = {}
    for f in br_files:
        key = get_episode_key(f)
        if key:
            br_map[key] = os.path.join(bluray_dir, f)
            
    matched_pairs = []
    for f in str_files:
        key = get_episode_key(f)
        if key in br_map:
            matched_pairs.append((br_map[key], os.path.join(streaming_dir, f), key))
            
    # Sort pairs sequentially by episode key
    matched_pairs.sort(key=lambda x: x[2])
    return matched_pairs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch cross-correlate timeline offsets between folder tracks over SMB/Samba.")
    parser.add_argument("-b", "--bluray_dir", required=True, help="Path to the directory containing Blu-ray source files")
    parser.add_argument("-s", "--streaming_dir", required=True, help="Path to the directory containing Streaming target files")
    parser.add_argument("-o", "--output", required=True, help="Path and name for the generated text report file")
    parser.add_argument("-d", "--duration", type=int, default=60, help="Duration of audio chunk to extract in seconds (default: 60)")
    
    args = parser.parse_args()
    
    print("Scanning directories for matching episodes...")
    pairs = match_directories(args.bluray_dir, args.streaming_dir)
    
    if not pairs:
        print("Error: No matching episodes could be paired between directories based on file names.")
        exit(1)
        
    print(f"Found {len(pairs)} matched episode pairs to process.\n")
    
    # Clean/initialize the output text file on a fresh run
    if os.path.exists(args.output):
        os.remove(args.output)
        
    for idx, (br_path, str_path, ep_key) in enumerate(pairs):
        print(f"--- Processing Batch [{idx + 1}/{len(pairs)}]: Episode Key ({ep_key.upper()}) ---")
        calculate_offset(
            file_bluray=br_path,
            file_streaming=str_path,
            duration=args.duration,
            output_txt=args.output,
            append_mode=True
        )
    
    print(f"\nAll done! Entire batch summary written to: {args.output}")