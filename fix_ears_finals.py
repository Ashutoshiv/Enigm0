import urllib.request
import os

def apply_patch():
    print("=== J.A.R.V.I.S. ABSOLUTE EAR PATCH ===")
    
    # 1. Create a stable, public folder for the models
    model_dir = os.path.join(os.getcwd(), "brain", "models")
    os.makedirs(model_dir, exist_ok=True)
    print(f"[*] Target Directory: {model_dir}")
    
    models = {
        "melspectrogram.tflite": "https://github.com/dscripka/openWakeWord/raw/v0.5.1/openwakeword/resources/models/melspectrogram.tflite",
        "embedding_model.tflite": "https://github.com/dscripka/openWakeWord/raw/v0.5.1/openwakeword/resources/models/embedding_model.tflite",
        "hey_jarvis_v0.1.tflite": "https://github.com/dscripka/openWakeWord/raw/v0.5.1/openwakeword/resources/models/hey_jarvis_v0.1.tflite"
    }
    
    for fname, url in models.items():
        target = os.path.join(model_dir, fname)
        if not os.path.exists(target):
            print(f"[*] Downloading {fname}...")
            urllib.request.urlretrieve(url, target)
        else:
            print(f"[+] {fname} already exists.")

    print("\n[***] ALL PATCHES SUCCESSFUL! Files are in ./brain/models")

if __name__ == "__main__":
    apply_patch()