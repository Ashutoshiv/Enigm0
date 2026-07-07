import uvicorn
import json
import asyncio
import threading
import time
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# --- AUTO-CLEANUP PROTOCOL ---
# Automatically delete the annoying lock file on boot so you never have to do it manually again!
lock_file_path = "jarvis_bot.lock"
if os.path.exists(lock_file_path):
    try:
        os.remove(lock_file_path)
        print("[*] Old jarvis_bot.lock file swept and deleted.")
    except Exception as e:
        print(f"[!] Could not delete lock file: {e}")

# --- THE TFLITE NEURAL BYPASS ---
import sys
import types
try:
    import tensorflow.lite as tflite
    tflite_runtime = types.ModuleType('tflite_runtime')
    tflite_runtime.interpreter = tflite
    sys.modules['tflite_runtime'] = tflite_runtime
    sys.modules['tflite_runtime.interpreter'] = tflite
    print("[*] TFLite Engine successfully bypassed using TensorFlow.")
except ImportError:
    pass
# --------------------------------

import master  

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def autonomous_voice_core():
    print("[*] Autonomous Voice Core Online. Awaiting 'Hey Jarvis'...")
    try:
        master.start_background_services()
    except Exception as e:
        print(f"[!] Background service error: {e}")
    
    time.sleep(2)
    try:
        master.speak("System online. I am running in the background, sir.")
    except Exception as e:
        print(f"[!] CRITICAL AUDIO ERROR: {e}")
    
    while True:
        try:
            if master.wait_for_wake_word():
                master.speak("I am here, sir.")
                
                is_active_session = True
                while is_active_session:
                    command = master.listen_for_command()
                    if not command:
                        master.speak("Standing by.")
                        is_active_session = False
                        continue
                        
                    # 1. THE STOP COMMAND: Instantly drops him back to background sleep
                    if any(word in command.lower() for word in ["stop", "shut down", "sleep", "exit", "goodbye", "jarvis stop", "cancel", "nevermind"]):
                        master.speak("Returning to standby, sir.")
                        is_active_session = False
                        continue
                    
                    # 2. NOISE FILTER: Ignore tiny background noises (coughs, chair squeaks)
                    if len(command.strip()) < 5:
                        continue
                    
                    print(f"[*] Voice Command Received: {command}")
                    ai_decision = master.ask_local_ai(command)
                    result_message = master.execute_command(ai_decision)
                    
                    # 3. SILENT EXECUTION: Prevent him from reading paragraphs of terminal output out loud
                    if ai_decision.get("action") in ["agent", "evolve", "cyber"]:
                        master.speak("Task execution complete, sir.")
                    else:
                        # Only speak full answers for casual chats, weather, or crypto
                        master.speak(result_message)
                    
        except Exception as e:
            print(f"[!] Voice Engine Error: {e}")
            time.sleep(2)

@app.on_event("startup")
def startup_event():
    print("[*] Web Server Online. Launching Voice Engine...")
    threading.Thread(target=autonomous_voice_core, daemon=True).start()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n[*] React UI connected to ENIGM0 via WebSockets!")
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_msg = payload.get("message", "")
            
            await websocket.send_json({"role": "system", "text": "Command received. Accessing neural pathways..."})
            
            master.active_chat_history.append(f"User: {user_msg}")
            
            def process_ai():
                ai_decision = master.ask_local_ai(user_msg)
                action = ai_decision.get("action", "chat")
                
                if action == "chat":
                    recent_memory = "\n".join(master.active_chat_history[-6:])
                    memory_injected_query = f"Recent Conversation Context:\n{recent_memory}\n\nUser's Current Command: {user_msg}"
                    ai_decision["target"] = memory_injected_query
                
                res = master.execute_command(ai_decision)
                master.active_chat_history.append(f"J.A.R.V.I.S.: {res}")
                return action, res
                
            action, result_message = await asyncio.to_thread(process_ai)
            
            await websocket.send_json({"role": "jarvis", "action": action, "text": result_message})
            asyncio.create_task(asyncio.to_thread(master.speak, result_message))
            
    except WebSocketDisconnect:
        print("\n[!] React UI Disconnected from WebSockets.")

if __name__ == "__main__":
    print("[*] J.A.R.V.I.S. Nexus API Online (Port 8000)")
    uvicorn.run(app, host="127.0.0.1", port=8000)