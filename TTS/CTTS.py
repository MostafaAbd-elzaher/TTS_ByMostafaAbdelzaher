# Interactive Emotional TTS - Select Emotion and Enter Text
import librosa
import soundfile as sf
import numpy as np
import tempfile
import os
import logging
import time
from TTS.api import TTS


def load_speaker_genders(path="speaker_audios/speaker_IDs.txt"):
    """Return a dict mapping speaker ID (normalized) -> gender string."""
    genders = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            # skip header if present
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                if i == 0 and line.lower().startswith("id,"):
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    sid = parts[0].strip()
                    g = parts[1].strip()
                    if sid:
                        genders[sid.upper()] = g
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return genders

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def create_emotional_tts(
    text,
    emotion="neutral",
    output_file="emotional_output.wav",
    speaker=None,
    tts_instance=None,
    speaker_gender=None,
    global_speed=1.0,
):
    """
    Create emotional TTS with different emotions using post-processing
    
    Emotions supported:
    - sad: lower pitch, slower speed, quieter
    - happy: higher pitch, faster speed, brighter
    - angry: lower pitch, faster speed, louder
    - calm: lower pitch, slower speed, softer
    - excited: higher pitch, faster speed, louder
    - neutral: normal settings
    """
    
    # Load or reuse TTS model (may download weights on first run)
    logging.info("Loading TTS model...")
    if tts_instance is not None:
        tts = tts_instance
    else:
        try:
            tts = TTS(model_name="tts_models/en/vctk/vits")
        except Exception as e:
            logging.error("Failed to initialize TTS model: %s", e)
            raise

    # Choose a speaker (use provided speaker, else first available or None)
    if speaker is None and getattr(tts, "speakers", None):
        try:
            speaker = tts.speakers[0]
        except Exception:
            speaker = None
    logging.info("Using speaker: %s (gender=%s)", speaker, speaker_gender)

    # Generate basic speech into a secure temporary file
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = tf.name
    tf.close()
    try:
        logging.info("Generating speech to temporary file %s...", temp_path)
        try:
            tts.tts_to_file(text=text, speaker=speaker, file_path=temp_path)
        except TypeError:
            # some TTS versions accept different param names
            tts.tts_to_file(text=text, file_path=temp_path)

        # Load the generated audio
        audio, sr = librosa.load(temp_path, sr=None)
    except Exception as e:
        logging.error("Error generating or loading TTS audio: %s", e)
        # cleanup temp file if exists
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise
    
    # Ensure audio is mono (librosa effects expect 1D array)
    if getattr(audio, "ndim", 1) > 1:
        audio = np.mean(audio, axis=1)

    # Apply emotional effects based on emotion type
    if emotion.lower() == "sad":
        # Sad: lower pitch, slower, quieter
        try:
            audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=-3)
        except Exception:
            pass
        # apply time-stretch using global_speed multiplier
        if len(audio) > sr:
            try:
                rate = 0.7 * float(global_speed)
                if abs(rate - 1.0) > 0.01 and rate > 0:
                    audio = librosa.effects.time_stretch(audio, rate=rate)
            except Exception:
                pass
        audio = audio * 0.8  # Quieter
        print("Applied sad emotion: lower pitch, slower speed, quieter volume")
        
    elif emotion.lower() == "happy":
        # Happy: higher pitch, faster, brighter
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=2)  # Higher pitch
        try:
            rate = 1.2 * float(global_speed)
            if len(audio) > sr and abs(rate - 1.0) > 0.01 and rate > 0:
                audio = librosa.effects.time_stretch(audio, rate=rate)
        except Exception:
            pass
        audio = audio * 1.1  # Slightly louder
        print("Applied happy emotion: higher pitch, faster speed, brighter tone")
        
    elif emotion.lower() == "angry":
        # Angry: lower pitch, faster, louder
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=-2)  # Lower pitch
        try:
            rate = 1.1 * float(global_speed)
            if len(audio) > sr and abs(rate - 1.0) > 0.01 and rate > 0:
                audio = librosa.effects.time_stretch(audio, rate=rate)
        except Exception:
            pass
        audio = audio * 1.2  # Louder
        print("Applied angry emotion: lower pitch, faster speed, louder volume")
        
    elif emotion.lower() == "calm":
        # Calm: lower pitch, slower, softer
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=-1)  # Slightly lower
        try:
            rate = 0.8 * float(global_speed)
            if len(audio) > sr and abs(rate - 1.0) > 0.01 and rate > 0:
                audio = librosa.effects.time_stretch(audio, rate=rate)
        except Exception:
            pass
        audio = audio * 0.9  # Softer
        print("Applied calm emotion: lower pitch, slower speed, softer volume")
        
    elif emotion.lower() == "excited":
        # Excited: higher pitch, faster, louder
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=3)  # Higher pitch
        try:
            rate = 1.3 * float(global_speed)
            if len(audio) > sr and abs(rate - 1.0) > 0.01 and rate > 0:
                audio = librosa.effects.time_stretch(audio, rate=rate)
        except Exception:
            pass
        audio = audio * 1.15  # Louder
        print("Applied excited emotion: higher pitch, faster speed, louder volume")
        
    elif emotion.lower() == "whisper":
        # Whisper: much quieter, slightly lower pitch
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=-1)  # Slightly lower
        audio = audio * 0.5  # Much quieter
        print("Applied whisper emotion: lower pitch, much quieter volume")
        
    else:  # neutral
        print("Applied neutral emotion: no modifications")
    
    # Prevent clipping and ensure float32
    audio = np.asarray(audio, dtype=np.float32)
    audio = np.clip(audio, -1.0, 1.0)

    try:
        sf.write(output_file, audio, sr, subtype='PCM_16')
    except TypeError:
        # older soundfile versions may not accept subtype kwarg
        sf.write(output_file, audio, sr)

    logging.info("Emotional TTS saved as: %s", output_file)

    # cleanup temp file
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass

    return output_file


# Available emotions
available_emotions = [
    "sad", "happy", "angry", "calm", "excited", "whisper", "neutral"
]


if __name__ == "__main__":
    print("🎭 Interactive Emotional Text-to-Speech")
    print("=" * 50)
    print("Available emotions:")
    for i, emotion in enumerate(available_emotions, 1):
        print(f"  {i}. {emotion.capitalize()}")

    print("\n" + "=" * 50)
    # Interactive Input Section
    print("🎤 Enter your text and select emotion:")
    print()

    # Get text input from user
    text = input("Enter the text you want to convert to speech: ")

    # Get emotion selection
    print("\nSelect emotion (enter number 1-7 or name):")
    emotion_choice = input("Your choice: ")
    ec = emotion_choice.strip().lower()

    selected_emotion = "neutral"
    if not ec:
        print("❌ Empty input. Using 'neutral' as default.")
    else:
        # If numeric, map to index
        if ec.isdigit():
            emotion_index = int(ec) - 1
            if 0 <= emotion_index < len(available_emotions):
                selected_emotion = available_emotions[emotion_index]
                print(f"\n✓ Selected emotion: {selected_emotion.capitalize()}")
            else:
                print("❌ Invalid number. Using 'neutral' as default.")
        else:
            # try matching by name
            matches = [e for e in available_emotions if e.lower() == ec]
            if matches:
                selected_emotion = matches[0]
                print(f"\n✓ Selected emotion: {selected_emotion.capitalize()}")
            else:
                print("❌ Unknown emotion name. Using 'neutral' as default.")

    print(f"\n📝 Text: '{text}'")
    print(f"😊 Emotion: {selected_emotion.capitalize()}")
    print("\n" + "=" * 50)
    # Generate Emotional Speech
    print("🎵 Generating emotional speech...")
    print()

    # Speaker selection: list available speakers (if any)
    tts_tmp = None
    try:
        tts_tmp = TTS(model_name="tts_models/en/vctk/vits")
    except Exception:
        tts_tmp = None

    chosen_speaker = None
    genders_map = load_speaker_genders()
    if tts_tmp and getattr(tts_tmp, "speakers", None):
        print("Available speakers:")
        for i, sp in enumerate(tts_tmp.speakers, 1):
            key = sp.strip().upper()
            g = genders_map.get(key, "unknown")
            print(f"  {i}. {sp}  (gender: {g})")
        sp_choice = input("Select speaker (number or exact name) or press Enter to use default: ")
        spc = sp_choice.strip()
        if spc:
            if spc.isdigit():
                idx = int(spc) - 1
                if 0 <= idx < len(tts_tmp.speakers):
                    chosen_speaker = tts_tmp.speakers[idx]
            else:
                # exact match
                matches = [s for s in tts_tmp.speakers if s == spc]
                if matches:
                    chosen_speaker = matches[0]
    # If model does not expose gender metadata, ask user optionally
    speaker_gender = None
    if chosen_speaker is not None:
        # try to find any gender metadata (model usually doesn't provide it)
        speaker_gender = None
        try:
            meta = getattr(tts_tmp, 'speakers_meta', None) or getattr(tts_tmp, 'speaker_meta', None)
            if isinstance(meta, dict) and chosen_speaker in meta:
                # try common keys
                val = meta[chosen_speaker]
                if isinstance(val, dict) and 'gender' in val:
                    speaker_gender = val.get('gender')
        except Exception:
            pass
        if speaker_gender is None:
            g = input("Optionally enter speaker gender (male/female/other) or press Enter to skip: ")
            if g.strip():
                speaker_gender = g.strip()

    # Ask for global speed multiplier (optional)
    gs = input("Enter global speed multiplier (e.g. 0.9 slower, 1.0 normal, 1.1 faster) or press Enter for 1.0: ")
    try:
        global_speed = float(gs) if gs.strip() else 1.0
    except Exception:
        global_speed = 1.0

    # Create output filename based on emotion and timestamp
    output_filename = f"my_{selected_emotion}_{int(time.time())}.wav"

    # Generate the emotional TTS
    try:
        result_file = create_emotional_tts(
            text,
            selected_emotion,
            output_filename,
            speaker=chosen_speaker,
            tts_instance=tts_tmp,
            speaker_gender=speaker_gender,
            global_speed=global_speed,
        )
        print(f"\n🎉 Success! Your emotional speech has been created!")
        print(f"📁 File saved as: {result_file}")
        print(f"🎧 You can now play the audio file to hear your {selected_emotion} speech!")
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        print("Please make sure you have the required dependencies installed.")
# Simple Function to Generate Emotional Speech
def generate_emotional_speech(text, emotion="neutral"):
    """
    Simple function to generate emotional speech
    
    Parameters:
    - text: The text you want to convert to speech
    - emotion: The emotion you want (sad, happy, angry, calm, excited, whisper, neutral)
    
    Returns:
    - The filename of the generated audio
    """
    
    # Validate emotion
    valid_emotions = ["sad", "happy", "angry", "calm", "excited", "whisper", "neutral"]
    if emotion.lower() not in valid_emotions:
        print(f"❌ Invalid emotion. Using 'neutral'. Valid emotions: {valid_emotions}")
        emotion = "neutral"
    
    # Create output filename
    output_file = f"emotional_{emotion}_{len(text[:20])}chars.wav"
    
    print(f"🎭 Generating {emotion} speech for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
    
    try:
        result = create_emotional_tts(text, emotion, output_file)
        print(f"✅ Success! Audio saved as: {result}")
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# Example usage:
print("📝 Example Usage:")
print("generate_emotional_speech('Hello world!', 'happy')")
print("generate_emotional_speech('I am so tired', 'sad')")
print("generate_emotional_speech('This is amazing!', 'excited')")
print("\n" + "=" * 50)
