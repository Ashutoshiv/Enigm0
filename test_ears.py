import sys
import types
import numpy as np
import pyaudio
import time

# --- 1. INJECT THE TFLITE BYPASS ---
try:
    import tensorflow.lite as tflite
    tflite_runtime = types.ModuleType('tflite_runtime')
    tflite_runtime.interpreter = tflite
    sys.modules['tflite_runtime'] = tflite_runtime
    sys.modules['tflite_runtime.interpreter'] = tflite
except ImportError:
    pass

from openwakeword.model import Model

def run_diagnostic():
    print("=== J.A.R.V.I.S. AUDIO DIAGNOSTIC TOOL ===")
    print("[*] Initializing neural audio cortex...")
    
    try:
        owwModel = Model(wakeword_models=["hey_jarvis_v0.1.tflite"])
        print("[+] Model loaded successfully!")
    except Exception as e:
        print(f"\n[!] ERROR LOADING MODEL: {e}")
        return

    print("[*] Opening microphone channel...")
    try:
        audio = pyaudio.PyAudio()
        mic_stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1280)
    except Exception as e:
        print(f"\n[!] MICROPHONE ERROR: {e}")
        return

    print("\n[***] MICROPHONE IS HOT [***]")
    print("Please speak loudly into your microphone.")
    print("If you do not see 'Vol' bars appearing below, Windows is muting Python!\n")

    try:
        while True:
            # Read audio from the mic
            audio_data = np.frombuffer(mic_stream.read(1280, exception_on_overflow=False), dtype=np.int16)
            
            # --- LIVE VOLUME METER ---
            peak_volume = np.max(np.abs(audio_data))
            if peak_volume > 300: # Only print if there is actual sound, not total silence
                vol_bar = "#" * int(peak_volume / 500)
                print(f"Vol: {peak_volume:05d} | {vol_bar}")
            
            # Feed it to the AI
            prediction = owwModel.predict(audio_data)
            
            # Get the score
            for mdl in owwModel.prediction_buffer.keys():
                score = prediction[mdl]
                
                # If the AI even slightly thinks it hears something, print it
                if score > 0.05:
                    bars = "|" * int(score * 20)
                    print(f"Listening... Confidence: [{score:.3f}] {bars}")
                    
                if score > 0.5:
                    print("\n[SUCCESS] WAKE WORD DETECTED! His ears are working perfectly!")
                    time.sleep(2) # Pause so you can read it
                    
    except KeyboardInterrupt:
        print("\n[*] Diagnostic terminated.")

if __name__ == "__main__":
    run_diagnostic()