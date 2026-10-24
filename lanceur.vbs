' Lanceur de l'assistant Telegram : demarre le bot sans fenetre
' et le relance automatiquement s'il s'arrete (plantage, coupure...).
Option Explicit
Dim sh, fso, dossier, py, script, code
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dossier = fso.GetParentFolderName(WScript.ScriptFullName)
py = dossier & "\.venv\Scripts\pythonw.exe"
script = dossier & "\transfert_telegram.py"
sh.CurrentDirectory = dossier
Do
  code = sh.Run("""" & py & """ """ & script & """", 0, True)
  If code = 3 Then Exit Do   ' deja lance ailleurs : on ne double pas
  WScript.Sleep 15000        ' attend 15 s puis relance
Loop
