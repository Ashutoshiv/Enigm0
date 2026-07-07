Set WshShell = CreateObject("WScript.Shell")
strCommand = "cmd /c cd /d ""C:\Users\ashut\Enigm0"" && venv\Scripts\python.exe -u api_server.py > jarvis_system_log.txt 2>&1"
WshShell.Run strCommand, 0, False