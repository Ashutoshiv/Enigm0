import subprocess
import json
import os
import re
import time
from groq import Groq
from dotenv import load_dotenv

# --- SECURE API KEYS VIA .ENV ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("[!] WARNING: GROQ_API_KEY missing from .env file!")

client = Groq(api_key=GROQ_API_KEY)

def plan_task(task_description):
    """The Swarm Manager: Breaks down massive tasks into logical steps."""
    print("\n[Swarm Manager] Analyzing massive task and drafting execution plan...")
    
    prompt = f"""You are the Manager of a 'God-Mode' AI Swarm. 
The user wants to accomplish this complex task: '{task_description}'
Break this down into 2 to 4 simple, sequential steps that a sysadmin or programmer could execute on a Windows PC.
Output ONLY a valid JSON object with a list called 'steps'.
Example: {{"steps": ["Check current IP address", "Ping google.com", "Save results to a file"]}}"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        plan = json.loads(completion.choices[0].message.content)
        return plan.get("steps", [task_description])
    except Exception as e:
        print(f"[!] Manager Error: {e}")
        return [task_description] # Failsafe: fall back to a single step

def execute_dynamic_task(task_description):
    """The Swarm Coordinator: Manages the Planner and the Iterative Engineer."""
    print(f"\n[***] SWARM INTELLIGENCE INITIATED [***]")
    
    # 1. The Manager drafts the plan
    steps = plan_task(task_description)
    
    print(f"\n[Swarm Manager] Task successfully broken down into {len(steps)} steps:")
    for i, step in enumerate(steps):
        print(f"  {i+1}. {step}")
        
    system_prompt = """You are Enigm0, the Swarm Engineer (a 'God-Mode' AI agent on Windows).
You execute tasks by writing terminal commands iteratively to accomplish the current step.

CRITICAL RULES:
1. NEVER use `Start-Process`, `-Verb RunAs`, or any command that triggers a Windows Admin UAC popup. 
2. NEVER write interactive commands (like `pause` or `Read-Host`). You run invisibly in the background.
3. Keep network commands simple (e.g., just run `arp -a` directly instead of trying to spawn new admin shells).
4. UI NAVIGATION (CRITICAL): NEVER guess X,Y mouse coordinates (they will be wrong). ALWAYS use keyboard shortcuts (`pyautogui.hotkey('win', 'r')`, `pyautogui.press('tab')`, `pyautogui.press('enter')`, `pyautogui.write()`) to control the PC. It is 100% reliable. Use `time.sleep(1)` between presses.

Tools:
1. PowerShell: <powershell> command </powershell>
2. Python: <python> code </python>
3. Step Complete: <done> Summary of what you achieved </done>

I will give you a step. You write code, I will give you the terminal output.
Keep writing code and reading output until the step is complete, then output <done>."""
    
    overall_summary = []
    
    # 2. The Engineer executes the plan step-by-step
    for i, step in enumerate(steps):
        print(f"\n[---] SWARM ENGINEER EXECUTING STEP {i+1}/{len(steps)}: {step} [---]")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current Step to execute: {step}"}
        ]
        
        step_solved = False
        
        # Give the Engineer up to 4 attempts to debug and solve this specific step
        for attempt in range(4): 
            print(f"[*] Engineer Thinking (Attempt {attempt+1}/4)...")
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1024
                )
                ai_response = completion.choices[0].message.content.strip()
                messages.append({"role": "assistant", "content": ai_response})
                
                # A) Did the Engineer finish the step?
                done_match = re.search(r'<done>(.*?)</done>', ai_response, re.DOTALL)
                if done_match:
                    result = done_match.group(1).strip()
                    print(f"[+] Step {i+1} Complete: {result}")
                    overall_summary.append(f"Step {i+1}: {result}")
                    step_solved = True
                    break
                    
                # B) Did the Engineer write PowerShell?
                ps_match = re.search(r'<powershell>(.*?)</powershell>', ai_response, re.DOTALL)
                if ps_match:
                    cmd = ps_match.group(1).strip()
                    print(f"[>] Running PowerShell:\n{cmd}")
                    try:
                        process = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True, timeout=20)
                        output = process.stdout.strip() + "\n" + process.stderr.strip()
                        if not output.strip(): output = "Command succeeded with no output."
                    except Exception as e:
                        output = f"Error: {e}"
                    print(f"[<] Terminal Output Received.")
                    messages.append({"role": "user", "content": f"Terminal Output:\n{output}"})
                    continue
                    
                # C) Did the Engineer write Python?
                py_match = re.search(r'<python>(.*?)</python>', ai_response, re.DOTALL)
                if py_match:
                    code = py_match.group(1).strip()
                    print(f"[>] Running Python Script...")
                    temp_script = "./skills/temp_agent_script.py"
                    with open(temp_script, "w", encoding="utf-8") as f: 
                        f.write(code)
                    try:
                        process = subprocess.run(["python", temp_script], capture_output=True, text=True, timeout=20)
                        output = process.stdout.strip() + "\n" + process.stderr.strip()
                        if not output.strip(): output = "Script succeeded with no output."
                    except Exception as e:
                        output = f"Error: {e}"
                    if os.path.exists(temp_script): 
                        os.remove(temp_script)
                    print(f"[<] Python Output Received.")
                    messages.append({"role": "user", "content": f"Python Output:\n{output}"})
                    continue
                    
                # Failsafe if he forgets tags
                messages.append({"role": "user", "content": "Error: You must wrap your response in <powershell>, <python>, or <done> tags. Try again."})
                
            except Exception as e:
                print(f"[!] Swarm Network Error: {e}")
                break
        
        if not step_solved:
            print(f"[!] Swarm Engineer failed to complete step {i+1}. Forcing progression to next step.")
            overall_summary.append(f"Step {i+1}: FAILED.")
            
        # Give the API a brief rest between major Swarm steps
        time.sleep(1) 
        
    final_report = "\n".join(overall_summary)
    return f"Swarm Execution Complete.\n{final_report}"

# Quick test block
if __name__ == "__main__":
    print(execute_dynamic_task("Open notepad visually, type 'Hello I am J.A.R.V.I.S', and leave it open on my screen."))