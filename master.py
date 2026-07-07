import os
import sys
import atexit
import time
import json
import threading
import subprocess
import uuid
import io # <--- NEW: For RAM-based audio processing
import speech_recognition as sr
import pyautogui
from groq import Groq
from dotenv import load_dotenv

# --- FILE LOCK: PREVENT TELEGRAM 409 CONFLICT ERRORS ---
LOCK_FILE = "jarvis_bot.lock"

def create_lock():
    """Prevents multiple instances of J.A.R.V.I.S. from running simultaneously."""
    if os.path.exists(LOCK_FILE):
        print("\n[!] CRITICAL ERROR: J.A.R.V.I.S. is already running in the background!")
        print("[!] Please close the existing instance or check Task Manager for 'pythonw.exe'.")
        sys.exit(1)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def remove_lock():
    """Removes the lock file when J.A.R.V.I.S. shuts down normally."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

create_lock()
atexit.register(remove_lock)

# --- NEW IMPORTS FOR MILLISECOND WAKE WORD ---
import openwakeword
from openwakeword.model import Model
import pyaudio
import numpy as np

# --- IMPORTING ALL JARVIS MODULES ---
from senses.voice import NeuralVoice
from senses.mobile_bridge import TelegramBridge
from senses.omni_logger import OmniLogger
from brain.vision import AssistantVision
from brain.cyber_search import search_threat_intelligence
from brain.cve_bridge import search_nvd_database
from skills.api_tools import route_api_request
from skills.agent_core import execute_dynamic_task
from skills.architect import evolve_system

try:
    from brain.memory import memory_core
except ImportError:
    class DummyMemory:
        def recall_memory(self, query): return ""
        def memorize(self, fact): return "Fact saved."
    memory_core = DummyMemory()

# --- SECURE API KEYS VIA .ENV ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GROQ_API_KEY:
    print("[!] WARNING: GROQ_API_KEY not found in .env file!")

client = Groq(api_key=GROQ_API_KEY)
voice_engine = NeuralVoice()
omni_logger = OmniLogger()

# Initialize Vision
try:
    vision_core = AssistantVision()
except Exception as e:
    print(f"[!] Vision module offline: {e}")
    vision_core = None

# Global Chat History for Deep Sleep Synthesis
active_chat_history = []

def speak(text):
    """Global speak function accessible by UI and modules."""
    voice_engine.speak(text)

# --- THE EARS (Hardware Wake Word) ---
def wait_for_wake_word():
    """Offline, millisecond-precise wake word detection using OpenWakeWord (100% Free)."""
    try:
        print("\n[Zzz...] Loading OpenWakeWord Model...")
        owwModel = Model(wakeword_models=['hey_jarvis'])
        
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1280
        
        audio = pyaudio.PyAudio()
        mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        print("\n[Zzz...] Hardware Ghost Loop Active. Say 'Hey Jarvis' to wake me...")

        while True:
            # Read audio chunk locally
            pcm = mic_stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(pcm, dtype=np.int16)
            
            # Process locally (NO INTERNET, NO API KEYS REQUIRED)
            prediction = owwModel.predict(audio_data)
            
            # Check if 'hey_jarvis' was detected with high confidence (Lowered to 0.40 for better hearing)
            for model_name, score in prediction.items():
                if score > 0.35: # LOWERED TO 0.35 FOR MAXIMUM WAKE WORD SENSITIVITY
                    print(f"\n[!] WAKE WORD DETECTED [!]")
                    mic_stream.stop_stream()
                    mic_stream.close()
                    audio.terminate()
                    return True

    except Exception as e:
        print(f"[!] OpenWakeWord Error: {e}")
        return _fallback_wake_word()

def _fallback_wake_word():
    """The old, slower Google Web API wake word method."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("\n[Zzz...] Ghost Loop Active (Google API). Waiting for 'Jarvis'...")
        while True:
            try:
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=3)
                text = recognizer.recognize_google(audio).lower()
                if "jarvis" in text:
                    return True
            except sr.UnknownValueError:
                pass 
            except sr.RequestError:
                time.sleep(2)

def listen_for_command():
    """Uses Groq Whisper API for flawless voice recognition, running entirely in RAM."""
    recognizer = sr.Recognizer()
    
    # 1. Faster Cutoff: Stop listening just 0.8 seconds after the user stops speaking
    recognizer.pause_threshold = 0.8  
    # 2. Dynamic Noise Filter: Automatically adjust to AC/fan/background noise
    recognizer.dynamic_energy_threshold = True 
    
    with sr.Microphone() as source:
        print("\n[>>>] J.A.R.V.I.S. IS LISTENING... [<<<]")
        
        # Quickly sample the room's background noise for 0.5 seconds to filter it out
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # 3. phrase_time_limit=15 prevents him from listening forever if a TV is playing
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            print("[*] Processing audio in RAM with Whisper-Large-v3...")
            
            # 4. RAM Processing: DO NOT save to hard drive. Process directly in memory!
            wav_data = audio.get_wav_data()
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "speech.wav" # Groq API requires a virtual filename
            
            transcription = client.audio.transcriptions.create(
              file=audio_file,
              model="whisper-large-v3",
              prompt="The user is speaking to their highly intelligent AI assistant J.A.R.V.I.S. Filter out background noise and ignore TV sounds.",
              temperature=0.0, # 0.0 makes the AI highly focused and prevents hallucinated words
              language="en" # Forces English to prevent translating background noise into random languages
            )
            
            text = transcription.text.strip()
            print(f"[User]: {text}")
            active_chat_history.append(f"User: {text}") 
            return text
            
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return "" 
        except Exception as e:
            print(f"[!] Audio Processing Error: {e}")
            return ""

# --- THE BRAIN (Groq LPU Router) ---
# ... existing code ...
def ask_local_ai(user_command):
    global active_chat_history
    past_context = memory_core.recall_memory(user_command)
    
    system_instruction = (
        "You are J.A.R.V.I.S., a hyper-intelligent, autonomous AI assistant. "
        "Analyze the user's intent and respond ONLY with a valid JSON object containing an 'action' and a 'target'. "
        "Valid actions: 'open', 'type', 'remember', 'chat', 'vision', 'api', 'agent', 'cyber', 'cve', or 'evolve'. "
        "Rules: "
        "1. SCREEN CONTROL (Clicking, scrolling, playing videos on screen): action='agent', target='Use pyautogui to press Tab multiple times and Enter to play the video.' "
        "2. GENERAL PC CONTROL/CODING: action='agent', target=exact instructions. "
        "3. OPENING A BRAND NEW WEBSITE OR APP: action='open', target='www.url.com' or 'app_name'. (Do NOT use this to interact with a page already open). "
        "4. UPGRADE/REWRITE SYSTEM SOURCE CODE: action='evolve', target=what to build/fix. "
        "5. Live Crypto Price: action='api', target='crypto:<coin_name>'. "
        "6. Live Weather: action='api', target='weather:<city_name>'. "
        "7. General Web Search: action='api', target='search:<query>'. "
        "8. Look at screen/What do you see: action='vision', target=the user's question. "
        "9. CYBERSECURITY/HACKING CONCEPTS (OWASP/MITRE): action='cyber', target=question. "
        "10. SPECIFIC VULNERABILITIES (NVD/CVSS): action='cve', target=query. "
        "11. General Conversation / Advice: action='chat', target=your intelligent, conversational response. "
        f"Relevant permanent memory: {past_context}"
    )
    
    try:
        # --- PROPER MEMORY INJECTION ---
        # Build the message chain starting with the system prompt
        messages_to_send = [{"role": "system", "content": system_instruction}]
        
        # Feed the last 10 messages to the AI so he remembers the active conversation
        for msg in active_chat_history[-10:]:
            if msg.startswith("User:"):
                # Prevent duplication if the message is already logged
                clean_msg = msg.replace("User:", "").strip()
                if clean_msg != user_command.strip():
                    messages_to_send.append({"role": "user", "content": clean_msg})
            elif msg.startswith("JARVIS:"):
                messages_to_send.append({"role": "assistant", "content": msg.replace("JARVIS:", "").strip()})
        
        # Add the current command at the very end
        messages_to_send.append({"role": "user", "content": user_command})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_to_send,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        result = json.loads(completion.choices[0].message.content)
        return result
    except Exception as e:
        print(f"[!] Brain Error: {e}")
        return {"action": "chat", "target": "I encountered an error in my neural routing system."}

# --- THE HANDS (Execution Engine) ---
# ... existing code ...
def execute_command(ai_response):
    if not ai_response:
        return "I had trouble thinking about that."
    
    action = ai_response.get("action")
    target = ai_response.get("target")
    
    if action == "api":
        response = route_api_request(target)
        active_chat_history.append(f"JARVIS: {response}")
        return response
    elif action == "agent":
        speak("Executing dynamic task...")
        response = execute_dynamic_task(target)
        active_chat_history.append(f"JARVIS: {response}")
        return response
    elif action == "evolve":
        speak("Initiating Architect Core. Designing system upgrade...")
        response = evolve_system(target)
        active_chat_history.append(f"JARVIS: {response}")
        return response
    elif action == "vision":
        speak("Accessing optical sensors...")
        if vision_core:
            response = vision_core.analyze_screen(target)
            active_chat_history.append(f"JARVIS: {response}")
            return response
        return "My vision module is offline."
    elif action == "cyber":
        speak("Accessing Threat Intelligence database...")
        intel_data = search_threat_intelligence(target)
        speak("Data retrieved. Analyzing tactics...")
        analysis_prompt = f"The user asked: '{target}'. Using ONLY this raw intelligence, provide a professional J.A.R.V.I.S. summary: {intel_data}"
        analysis_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.3
        )
        response = analysis_completion.choices[0].message.content
        active_chat_history.append(f"JARVIS: {response}")
        return response
    elif action == "cve":
        speak("Querying cloud vulnerability database...")
        cve_data = search_nvd_database(target)
        speak("Analyzing vulnerability metrics...")
        analysis_prompt = f"The user asked: '{target}'. Using ONLY this raw database info, summarize the vulnerability, severity score, and impact. Data: {cve_data}"
        analysis_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.2
        )
        response = analysis_completion.choices[0].message.content
        active_chat_history.append(f"JARVIS: {response}")
        return response
    elif action == "chat":
        active_chat_history.append(f"JARVIS: {target}")
        return target
    elif action == "remember":
        memory_core.memorize(target)
        return "I have committed that to my permanent memory."
    elif action == "open":
        try:
            os.system(f"start {target}")
            return f"Opening {target}."
        except:
            return f"Failed to open {target}."
    elif action == "type":
        pyautogui.write(target, interval=0.05)
        return "Typing completed."
        
    return "I didn't understand the required action."

# --- DEEP SLEEP SYNTHESIS (Self-Learning) ---
def synthesize_memory():
    global active_chat_history
    if len(active_chat_history) < 2:
        return
    
    print("[*] Initiating Deep Sleep Synthesis...")
    history_text = "\n".join(active_chat_history)
    prompt = (
        "You are J.A.R.V.I.S.'s memory architect. Read the following conversation and extract ONLY new, permanent facts about the user "
        "(preferences, goals, ongoing problems, name, occupation). If nothing important was said, output 'NONE'. "
        f"Conversation:\n{history_text}"
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        facts = completion.choices[0].message.content.strip()
        if facts != "NONE" and facts != "":
            print(f"[*] Synthesis Complete. Saving new facts: {facts}")
            memory_core.memorize(facts)
        else:
            print("[*] Synthesis Complete. No new permanent data detected.")
    except Exception as e:
        print(f"[!] Synthesis Error: {e}")
        
    active_chat_history = []

# --- BACKGROUND SERVICES ---
def start_background_services():
    """Starts the Telegram Mobile Bridge invisibly."""
    omni_logger.start()
    if TELEGRAM_BOT_TOKEN:
        try:
            telegram_bridge = TelegramBridge(TELEGRAM_BOT_TOKEN, ask_local_ai, execute_command)
            telegram_bridge.run_in_background() 
            print("[*] Mobile Bridge Online. Telegram bot listening in background.")
        except Exception as e:
            print(f"[!] Mobile Bridge failed to start: {e}")

# --- MAIN LOOP (Terminal Fallback) ---
def main():
    start_background_services()
    speak("System is online. Master core operational.")
    
    while True:
        if wait_for_wake_word():
            speak("I am here, sir.")
            is_active_session = True
            
            while is_active_session:
                command = listen_for_command()
                
                if not command:
                    print("\n[*] Conversation paused. Archiving data and returning to sleep.")
                    speak("Archiving session data. I will be on standby.")
                    synthesize_memory()
                    is_active_session = False
                    continue

                if command in ["stop", "shut down", "sleep", "exit", "terminate", "goodbye"]:
                    speak("Shutting down the central nervous system. Goodbye, sir.")
                    sys.exit()

                print(f"[*] Analyzing Command: {command}")
                ai_decision = ask_local_ai(command)
                result_message = execute_command(ai_decision)
                speak(result_message)

if __name__ == "__main__":
    main()