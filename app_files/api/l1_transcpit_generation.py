import os
import logging
import tempfile
from pydub import AudioSegment
from moviepy import VideoFileClip
from openai import AzureOpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import config

# Load environment variables
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_API_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT_ID = os.getenv("AZURE_OPENAI_SPEECH_DEPLOYMENT")

CHUNK_DURATION_MIN = config.chunk_size
MAX_WORKERS = config.chunk_thread
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
def extract_audio_to_tempfile(video_path):
    try:
        logging.info(f"Extracting audio from: {video_path}")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(temp_audio_path, logger=None)
        clip.close()
        return temp_audio_path
    except Exception as e:
        logging.error(f"Failed to extract audio: {e}")
        return None

def split_mp3_to_tempfiles(mp3_path, chunk_duration_minutes=20):
    try:
        audio = AudioSegment.from_mp3(mp3_path)
        chunk_length_ms = chunk_duration_minutes * 60 * 1000
        chunks = []

        for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
            chunk = audio[start:start + chunk_length_ms]
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_chunk_file:
                chunk.export(temp_chunk_file.name, format="mp3")
                chunks.append((i, temp_chunk_file.name))

        return chunks
    except Exception as e:
        logging.error(f"Error while splitting audio: {e}")
        return []

def transcribe_chunk(index, file_path):
    try:
        tick1 = time.time()
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=config.transcribe_azure_api_version,
            azure_endpoint=AZURE_API_ENDPOINT,
        )
        with open(file_path, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                file=audio_file,
                model=DEPLOYMENT_ID
            )
        toc1 = time.time()
        logging.info(f"Transcription for chunk {index} completed in {toc1 - tick1:.2f} seconds")
        return index, result.text
    except Exception as e:
        logging.error(f"Transcription failed for chunk {index}: {e}")
        return index, ""
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def process_videos(video_files):
    if not video_files:
        logging.info("No video files to process.")
        return ""

    final_transcript = ""

    for video_path in video_files:
        logging.info(f"Processing video: {video_path}")

        audio_path = extract_audio_to_tempfile(video_path)
        if not audio_path:
            continue

        chunks = split_mp3_to_tempfiles(audio_path, CHUNK_DURATION_MIN)
        os.remove(audio_path)  # Clean up main audio

        transcriptions = [None] * len(chunks)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_index = {
                executor.submit(transcribe_chunk, idx, path): idx for idx, path in chunks
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    index, text = future.result()
                    transcriptions[index] = text
                except Exception as e:
                    logging.error(f"Exception in transcription thread {idx}: {e}")
                    transcriptions[idx] = ""

        video_transcript = "\n".join(filter(None, transcriptions))
        final_transcript += video_transcript + "\n"

    return final_transcript.strip()

def process_audio(mp3_path):
    if not os.path.isfile(mp3_path) or not mp3_path.endswith(".mp3"):
        logging.error("Invalid MP3 path provided.")
        return ""

    chunks = split_mp3_to_tempfiles(mp3_path, CHUNK_DURATION_MIN)
    if not chunks:
        return ""

    transcriptions = [None] * len(chunks)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_index = {
            executor.submit(transcribe_chunk, idx, path): idx for idx, path in chunks
        }

        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                index, text = future.result()
                transcriptions[index] = text
            except Exception as e:
                logging.error(f"Transcription failed for chunk {idx}: {e}")
                transcriptions[idx] = ""

    return "\n".join(filter(None, transcriptions)).strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tic1=time.time()
    videos = ["input.mp4"]  # Replace with actual paths
    result = process_videos(videos)
    toc1 = time.time()
    logging.info(f"Total processing time: {toc1 - tic1:.2f} seconds")
    print("Total processing time:", toc1 - tic1)
    print(result)
