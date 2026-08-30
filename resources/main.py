import json
import os
import queue
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from kivy.utils import platform
except ImportError:
    platform = "unknown"


APP_NAME = "HACK DROID BUILDER"
APP_VERSION = "1.0.0"
PYTHON_VERSION = "3.9"
KIVY_VERSION = "2.2.0"
DEFAULT_CODE = '''from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class HackDroidApp(App):
    def build(self):
        panel = BoxLayout(
            orientation="vertical",
            padding=24,
            spacing=12,
        )
        panel.add_widget(Label(text="> HACK DROID ONLINE"))
        panel.add_widget(Label(text="# device ready"))
        return panel


if __name__ == "__main__":
    HackDroidApp().run()
'''

PERMISSIONS = [
    "INTERNET",
    "ACCESS_NETWORK_STATE",
    "ACCESS_WIFI_STATE",
    "CHANGE_WIFI_STATE",
    "ACCESS_FINE_LOCATION",
    "ACCESS_COARSE_LOCATION",
    "BLUETOOTH",
    "BLUETOOTH_ADMIN",
    "BLUETOOTH_CONNECT",
    "BLUETOOTH_SCAN",
    "BLUETOOTH_ADVERTISE",
    "NFC",
    "CAMERA",
    "RECORD_AUDIO",
    "VIBRATE",
    "READ_MEDIA_IMAGES",
    "READ_MEDIA_VIDEO",
    "READ_MEDIA_AUDIO",
    "READ_EXTERNAL_STORAGE",
    "WRITE_EXTERNAL_STORAGE",
    "POST_NOTIFICATIONS",
    "FOREGROUND_SERVICE",
    "WAKE_LOCK",
    "RECEIVE_BOOT_COMPLETED",
    "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS",
    "USE_BIOMETRIC",
    "BODY_SENSORS",
    "ACTIVITY_RECOGNITION",
    "READ_CONTACTS",
    "WRITE_CONTACTS",
    "READ_CALENDAR",
    "WRITE_CALENDAR",
    "READ_CALL_LOG",
    "WRITE_CALL_LOG",
    "READ_PHONE_STATE",
    "CALL_PHONE",
    "SEND_SMS",
    "READ_SMS",
    "RECEIVE_SMS",
    "INSTALL_PACKAGES",
]

TEMPLATES = {
    "Empty": DEFAULT_CODE,
    "HackDroid": '''from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class HackDroidApp(App):
    def build(self):
        panel = BoxLayout(orientation="vertical", padding=24, spacing=12)
        panel.add_widget(Label(text="> HACK DROID ONLINE"))
        panel.add_widget(Label(text="# device ready"))
        return panel


HackDroidApp().run()
''',
    "WiFi": '''from kivy.app import App
from kivy.uix.label import Label


class WifiApp(App):
    def build(self):
        return Label(text="WiFi scanner ready")


WifiApp().run()
''',
    "NFC": '''from kivy.app import App
from kivy.uix.label import Label


class NfcApp(App):
    def build(self):
        return Label(text="NFC reader ready")


NfcApp().run()
''',
    "BT": '''from kivy.app import App
from kivy.uix.label import Label


class BluetoothApp(App):
    def build(self):
        return Label(text="Bluetooth discovery ready")


BluetoothApp().run()
''',
    "Sensors": '''from kivy.app import App
from kivy.uix.label import Label


class SensorApp(App):
    def build(self):
        return Label(text="Motion sensors ready")


SensorApp().run()
''',
    "FileManager": '''from pathlib import Path
from kivy.app import App
from kivy.uix.label import Label


class FilesApp(App):
    def build(self):
        names = [item.name for item in Path(".").iterdir()]
        return Label(text="Files:\\n" + "\\n".join(names))


FilesApp().run()
''',
}


def external_storage():
    if platform == "android":
        try:
            from android.storage import primary_external_storage_path

            return Path(primary_external_storage_path())
        except Exception:
            return Path("/sdcard")
    return Path.home() / "HackDroidBuilds"


def safe_name(value):
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return cleaned.strip("-") or "hackdroid-project"


class TerminalLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", "DroidSansMono")
        kwargs.setdefault("color", (0.55, 1, 0.35, 1))
        super().__init__(**kwargs)


class TerminalButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_color", (0.05, 0.12, 0.07, 1))
        kwargs.setdefault("color", (0.55, 1, 0.35, 1))
        kwargs.setdefault("font_name", "DroidSansMono")
        kwargs.setdefault("font_size", dp(12))
        super().__init__(**kwargs)


class HackDroidBuilder(App):
    status = StringProperty("ready")

    def build(self):
        Window.clearcolor = (0.015, 0.025, 0.018, 1)
        self.log_queue = queue.Queue()
        self.build_process = None
        self.permission_boxes = {}
        self.code = DEFAULT_CODE
        self.settings = {
            "name": "HackDroid Project",
            "package": "org.hackdroid.project",
            "version": "1.0.0",
            "sdk": "34",
            "icon": "icon.png",
            "mode": "debug",
            "arch": "arm64-v8a",
            "compression": "balanced",
            "optimization": True,
            "permissions": ["INTERNET"],
        }
        self.build_root = external_storage() / "HackDroidBuilds"
        self.build_root.mkdir(parents=True, exist_ok=True)

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        root.add_widget(self.make_header())
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(5))
        self.content = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        root.add_widget(self.scroll)
        Clock.schedule_interval(self.consume_logs, 0.1)
        self.add_sections()
        return root

    def make_header(self):
        header = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(10))
        title = BoxLayout(orientation="vertical")
        title.add_widget(TerminalLabel(text="@ HACK DROID", font_size=dp(13), bold=True))
        title.add_widget(TerminalLabel(text="BUILDER", font_size=dp(27), bold=True))
        title.add_widget(TerminalLabel(text=f"v{APP_VERSION} - ANDROID 8.0+", font_size=dp(10)))
        header.add_widget(title)
        badge = TerminalLabel(text="O LOCAL", size_hint_x=None, width=dp(80), font_size=dp(11))
        header.add_widget(badge)
        return header

    def section(self, symbol, title, hint=""):
        box = GridLayout(cols=1, spacing=dp(8), padding=dp(12), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        heading = BoxLayout(size_hint_y=None, height=dp(24))
        heading.add_widget(TerminalLabel(text=f"{symbol} {title}", font_size=dp(14), bold=True))
        heading.add_widget(TerminalLabel(text=hint, font_size=dp(10), halign="right"))
        box.add_widget(heading)
        self.content.add_widget(box)
        return box

    def field(self, parent, label, value, key, multiline=False):
        parent.add_widget(TerminalLabel(text=label, font_size=dp(10), size_hint_y=None, height=dp(18)))
        editor = TextInput(
            text=value,
            multiline=multiline,
            size_hint_y=None,
            height=dp(42 if not multiline else 240),
            background_color=(0.01, 0.02, 0.015, 1),
            foreground_color=(0.75, 1, 0.58, 1),
            cursor_color=(0.55, 1, 0.35, 1),
            padding=[dp(10), dp(10)],
            font_name="DroidSansMono",
            font_size=dp(12),
        )
        parent.add_widget(editor)
        setattr(self, f"{key}_input", editor)
        return editor

    def add_sections(self):
        project = self.section("#", "PROJECT SETTINGS", "01")
        self.field(project, "APP NAME", self.settings["name"], "name")
        self.field(project, "PACKAGE NAME", self.settings["package"], "package")
        self.field(project, "VERSION", self.settings["version"], "version")
        self.field(project, "SDK LEVEL", self.settings["sdk"], "sdk")
        self.field(project, "ICON FILE", self.settings["icon"], "icon")

        editor = self.section(">", "CODE EDITOR", "PYTHON 3.9")
        self.code_input = TextInput(
            text=self.code,
            multiline=True,
            size_hint_y=None,
            height=dp(330),
            background_color=(0.005, 0.01, 0.006, 1),
            foreground_color=(0.55, 1, 0.35, 1),
            cursor_color=(0.55, 1, 0.35, 1),
            padding=[dp(12), dp(12)],
            font_name="DroidSansMono",
            font_size=dp(12),
        )
        editor.add_widget(self.code_input)

        permissions = self.section("@", "PERMISSIONS", f"{len(PERMISSIONS)} AVAILABLE")
        for permission in PERMISSIONS:
            row = BoxLayout(size_hint_y=None, height=dp(32))
            box = CheckBox(size_hint_x=None, width=dp(42), active=permission in self.settings["permissions"])
            self.permission_boxes[permission] = box
            row.add_widget(box)
            row.add_widget(TerminalLabel(text=permission, font_size=dp(10)))
            permissions.add_widget(row)

        build = self.section("=", "BUILD SETTINGS", "02")
        mode_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        mode_row.add_widget(TerminalLabel(text="BUILD TYPE", font_size=dp(10)))
        self.mode_spinner = Spinner(text="debug", values=("debug", "release"), size_hint_x=None, width=dp(120))
        mode_row.add_widget(self.mode_spinner)
        mode_row.add_widget(TerminalLabel(text="ARCH", font_size=dp(10)))
        self.arch_spinner = Spinner(text="arm64-v8a", values=("arm64-v8a", "armeabi-v7a", "x86_64"), size_hint_x=None, width=dp(130))
        mode_row.add_widget(self.arch_spinner)
        build.add_widget(mode_row)
        compression_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        compression_row.add_widget(TerminalLabel(text="COMPRESSION", font_size=dp(10)))
        self.compression_spinner = Spinner(text="balanced", values=("balanced", "maximum", "none"), size_hint_x=None, width=dp(130))
        compression_row.add_widget(self.compression_spinner)
        compression_row.add_widget(TerminalLabel(text="OPTIMIZE", font_size=dp(10)))
        self.optimization_box = CheckBox(active=True, size_hint_x=None, width=dp(45))
        compression_row.add_widget(self.optimization_box)
        build.add_widget(compression_row)

        compile_box = self.section("O", "COMPILE APK", "GITHUB / COLAB")
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(10))
        compile_box.add_widget(self.progress)
        self.compile_button = TerminalButton(text="> BUILD APK", size_hint_y=None, height=dp(46))
        self.compile_button.bind(on_release=self.start_build)
        compile_box.add_widget(self.compile_button)
        self.log_output = TextInput(
            text="> builder ready\n# use GitHub Actions or Colab for Android compilation\n",
            readonly=True,
            multiline=True,
            size_hint_y=None,
            height=dp(150),
            background_color=(0.005, 0.01, 0.006, 1),
            foreground_color=(0.45, 0.8, 0.35, 1),
            padding=[dp(10), dp(10)],
            font_name="DroidSansMono",
            font_size=dp(10),
        )
        compile_box.add_widget(self.log_output)

        output = self.section("°", "OUTPUT", "APK FILE")
        self.output_label = TerminalLabel(text="> no APK found", font_size=dp(11), size_hint_y=None, height=dp(30))
        output.add_widget(self.output_label)
        output_buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        for text, callback in (
            ("INSTALL", self.install_apk),
            ("SHARE", self.share_apk),
            ("DELETE", self.delete_apk),
        ):
            button = TerminalButton(text=text)
            button.bind(on_release=callback)
            output_buttons.add_widget(button)
        output.add_widget(output_buttons)

        templates = self.section("-", "TEMPLATES", "STARTER CODE")
        template_row = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        template_row.bind(minimum_height=template_row.setter("height"))
        for name in TEMPLATES:
            button = TerminalButton(text=name, size_hint_y=None, height=dp(42))
            button.bind(on_release=lambda _, selected=name: self.load_template(selected))
            template_row.add_widget(button)
        templates.add_widget(template_row)

        projects = self.section("=", "PROJECTS", "LOCAL FILES")
        project_buttons = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(88))
        for text, callback in (
            ("SAVE", self.save_project),
            ("LOAD", self.load_project),
            ("EXPORT", self.export_project),
            ("IMPORT", self.import_project),
        ):
            button = TerminalButton(text=text)
            button.bind(on_release=callback)
            project_buttons.add_widget(button)
        projects.add_widget(project_buttons)
        projects.add_widget(TerminalLabel(text=f"storage = {self.build_root}", font_size=dp(9), size_hint_y=None, height=dp(28)))

        footer = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(45))
        footer.add_widget(TerminalLabel(text="# no PC  -  no terminal  -  no external tools", font_size=dp(9), halign="center"))
        footer.add_widget(TerminalLabel(text="HACK DROID BUILDER ° LOCAL FIRST", font_size=dp(9), halign="center"))
        self.content.add_widget(footer)

    def collect_settings(self):
        for key in ("name", "package", "version", "sdk", "icon"):
            self.settings[key] = getattr(self, f"{key}_input").text.strip()
        self.settings["mode"] = self.mode_spinner.text
        self.settings["arch"] = self.arch_spinner.text
        self.settings["compression"] = self.compression_spinner.text
        self.settings["optimization"] = self.optimization_box.active
        self.settings["permissions"] = [
            permission for permission, checkbox in self.permission_boxes.items() if checkbox.active
        ]
        self.code = self.code_input.text
        return self.settings

    def project_path(self):
        return self.build_root / f"{safe_name(self.settings['name'])}.json"

    def save_project(self, *_):
        self.collect_settings()
        payload = {"settings": self.settings, "code": self.code, "saved_at": datetime.now().isoformat()}
        self.project_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.write_build_files()
        self.set_status(f"saved = {self.project_path().name}")

    def load_project(self, *_):
        files = sorted(self.build_root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not files:
            self.set_status("no saved project")
            return
        payload = json.loads(files[0].read_text(encoding="utf-8"))
        self.settings.update(payload.get("settings", {}))
        self.code = payload.get("code", DEFAULT_CODE)
        self.apply_settings()
        self.set_status(f"loaded = {files[0].name}")

    def export_project(self, *_):
        self.collect_settings()
        self.write_build_files()
        archive = self.build_root / f"{safe_name(self.settings['name'])}-source"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / "main.py").write_text(self.code, encoding="utf-8")
        (archive / "buildozer.spec").write_text(self.make_spec(), encoding="utf-8")
        self.set_status(f"exported = {archive}")

    def import_project(self, *_):
        files = sorted(self.build_root.glob("*/main.py"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not files:
            self.set_status("no exported source found")
            return
        self.code = files[0].read_text(encoding="utf-8")
        self.code_input.text = self.code
        self.set_status(f"imported = {files[0].parent.name}")

    def apply_settings(self):
        for key in ("name", "package", "version", "sdk", "icon"):
            getattr(self, f"{key}_input").text = self.settings.get(key, "")
        self.mode_spinner.text = self.settings.get("mode", "debug")
        self.arch_spinner.text = self.settings.get("arch", "arm64-v8a")
        self.compression_spinner.text = self.settings.get("compression", "balanced")
        self.optimization_box.active = self.settings.get("optimization", True)
        active = set(self.settings.get("permissions", []))
        for permission, checkbox in self.permission_boxes.items():
            checkbox.active = permission in active
        self.code_input.text = self.code

    def load_template(self, name):
        self.code = TEMPLATES[name]
        self.code_input.text = self.code
        self.set_status(f"template loaded = {name}")

    def make_spec(self):
        settings = self.collect_settings()
        permissions = ",".join(settings["permissions"])
        requirements = "python3,kivy==2.2.0"
        return f"""[app]
title = {settings["name"]}
package.name = {safe_name(settings["package"].split(".")[-1])}
package.domain = {".".join(settings["package"].split(".")[:-1]) or "org.hackdroid"}
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
version = {settings["version"]}
requirements = {requirements}
orientation = portrait
fullscreen = 0
android.permissions = {permissions}
android.api = {settings["sdk"]}
android.minapi = 26
android.ndk = 25b
android.archs = {settings["arch"]}
android.accept_sdk_license = True
android.private_storage = True
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
"""

    def write_build_files(self):
        project = self.build_root / safe_name(self.settings["name"])
        project.mkdir(parents=True, exist_ok=True)
        (project / "main.py").write_text(self.code, encoding="utf-8")
        (project / "buildozer.spec").write_text(self.make_spec(), encoding="utf-8")
        return project

    def start_build(self, *_):
        self.collect_settings()
        self.write_build_files()
        if self.build_process is not None and self.build_process.poll() is None:
            self.set_status("build already running")
            return
        if shutil.which("buildozer") is None:
            self.append_log("> buildozer not installed on this device")
            self.append_log("# source exported; run .github/workflows/build.yml or Colab")
            self.set_status("use GitHub Actions or Colab")
            return
        project = self.build_root / safe_name(self.settings["name"])
        command = ["buildozer", "android", self.settings["mode"]]
        self.progress.value = 0
        self.compile_button.disabled = True
        self.append_log(f"> running {' '.join(command)}")
        threading.Thread(target=self.build_command, args=(project, command), daemon=True).start()

    def build_command(self, project, command):
        try:
            self.build_process = subprocess.Popen(
                command,
                cwd=project,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in self.build_process.stdout:
                self.log_queue.put(line.rstrip())
            result = self.build_process.wait()
            self.log_queue.put(f"> build exit code = {result}")
            self.log_queue.put(("BUILD_OK" if result == 0 else "BUILD_FAILED"))
        except Exception as error:
            self.log_queue.put(f"> build error = {error}")
            self.log_queue.put("BUILD_FAILED")

    def consume_logs(self, *_):
        while not self.log_queue.empty():
            line = self.log_queue.get()
            if line == "BUILD_OK":
                self.progress.value = 100
                self.compile_button.disabled = False
                self.set_status("APK ready")
                self.find_apk()
            elif line == "BUILD_FAILED":
                self.compile_button.disabled = False
                self.set_status("build failed")
            else:
                self.append_log(line)
                if "%" in line:
                    try:
                        percent = int(line.split("%", 1)[0].split()[-1])
                        self.progress.value = min(100, max(0, percent))
                    except ValueError:
                        pass

    def find_apk(self):
        apks = sorted(self.build_root.rglob("*.apk"), key=lambda path: path.stat().st_mtime, reverse=True)
        if apks:
            self.output_label.text = f"> {apks[0].name}\n  {apks[0]}"
        else:
            self.output_label.text = "> build finished, APK not found"

    def install_apk(self, *_):
        apks = sorted(self.build_root.rglob("*.apk"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not apks:
            self.set_status("no APK to install")
            return
        if platform != "android":
            self.set_status(f"APK ready = {apks[0]}")
            return
        try:
            from jnius import autoclass

            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(Uri.parse(f"file://{apks[0]}"), "application/vnd.android.package-archive")
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
            self.set_status("installer opened")
        except Exception as error:
            self.set_status(f"install error = {error}")

    def share_apk(self, *_):
        apks = sorted(self.build_root.rglob("*.apk"), key=lambda path: path.stat().st_mtime, reverse=True)
        self.set_status(f"share file = {apks[0]}" if apks else "no APK to share")

    def delete_apk(self, *_):
        removed = 0
        for apk in self.build_root.rglob("*.apk"):
            apk.unlink()
            removed += 1
        self.output_label.text = "> no APK found"
        self.set_status(f"deleted = {removed}")

    def append_log(self, line):
        current = self.log_output.text.rstrip()
        self.log_output.text = f"{current}\n{line}" if current else line
        self.log_output.cursor = (0, len(self.log_output.text))

    def set_status(self, value):
        self.status = value
        self.append_log(f"# {value}")

    def on_stop(self):
        if self.build_process is not None and self.build_process.poll() is None:
            self.build_process.terminate()


if __name__ == "__main__":
    HackDroidBuilder().run()