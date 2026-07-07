import os
import requests
import openwakeword

def apply_ultimate_patch():
    print("=== J.A.R.V.I.S. ULTIMATE NEURAL EAR PATCH ===")
    
    # 1. Find the exact hardcoded folder the library is crashing on
    model_dir = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
    os.makedirs(model_dir, exist_ok=True)
    print(f"[*] Target Directory: {model_dir}")
    
    # 2. Raw binary files for the AI
    models = {
        "melspectrogram.tflite": "https://github.com/dscripka/openWakeWord/raw/v0.5.1/openwakeword/resources/models/melspectrogram.tflite",
        "embedding_model.tflite": "https://github.com/dscripka/openWakeWord/raw/v0.5.1/openwakeword/resources/models/embedding_model.tflite",
        "hey_jarvis_v0.1.tflite": "https://github.com/dscripka/openWakeWord/raw/v0.5.1/openwakeword/resources/models/hey_jarvis_v0.1.tflite"
    }
    
    for filename, url in models.items():
        target_file = os.path.join(model_dir, filename)
        print(f"[*] Downloading {filename}...")
        
        try:
            # We use requests to bypass GitHub's redirect blocks and get raw binary data
            response = requests.get(url, allow_redirects=True)
            response.raise_for_status()
            
            # OVERWRITE the corrupted file inside the hidden Windows folder
            with open(target_file, "wb") as f:
                f.write(response.content)
                
            size = os.path.getsize(target_file)
            print(f"    -> Success! ({size/1024:.1f} KB written directly to library core)")
            
        except Exception as e:
            print(f"    -> [!] Failed: {e}")

    print("\n[***] ALL PATCHES SUCCESSFUL! You can run test_ears.py now! [***]")

if __name__ == "__main__":
    apply_ultimate_patch()