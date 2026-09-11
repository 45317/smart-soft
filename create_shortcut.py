import os
import sys
import subprocess


def create_icon():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (256, 256), (33, 150, 243, 255))
    dc = ImageDraw.Draw(img)
    dc.rectangle([32, 32, 224, 224], fill=(255, 255, 255, 255))
    dc.rectangle([56, 56, 200, 200], fill=(33, 150, 243, 255))
    dc.text((72, 70), "SS", fill=(255, 255, 255, 255))

    icon_path = os.path.join(os.environ["TEMP"], "smartsoft.ico")
    img.save(icon_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    return icon_path


def create_shortcut():
    icon_path = create_icon()
    desktop = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop")
    shortcut_path = os.path.join(desktop, "SmartSoft.lnk")
    python_exe = sys.executable
    launcher = os.path.abspath("launcher.py")
    workdir = os.path.abspath(".")

    ps_script = f'''
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut("{shortcut_path}")
$shortcut.TargetPath = "{python_exe}"
$shortcut.Arguments = "launcher.py"
$shortcut.WorkingDirectory = "{workdir}"
$shortcut.IconLocation = "{icon_path},0"
$shortcut.Description = "SmartSoft - AI Assistant"
$shortcut.Save()
'''
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
    print(f"Shortcut created: {shortcut_path}")


if __name__ == "__main__":
    create_shortcut()
