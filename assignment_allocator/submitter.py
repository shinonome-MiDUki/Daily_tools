"""
MyAssignment — assignment file organiser
"""

# ── 標準ライブラリ ────────────────────────────────────────
import datetime
import json
import os
import platform
import re
import subprocess
import shutil
import sys
import tty
import termios

from pathlib import Path


# ── 定数 ──────────────────────────────────────────────────

DAY_OF_WEEK_REF = {
    "1": "月", "2": "火", "3": "水", "4": "木",
    "5": "金", "6": "土", "7": "日",
}
DAY_OF_WEEK_REF_ENG = {
    "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu",
    "5": "Fri", "6": "Sat", "7": "Sun",
}
CONFIG: dict = {
    "use_weekday": True,
    "include_weekends": False,
    "dive_layer": 1,
}
CONFIG_CONVENTION: dict[str, str] = {
    "use_weekday": "Use the day-of-a-week based allocation system",
    "include_weekends": "Include weekends in your file system",
    "dive_layer": "The number of dive layers",
}

_HELP_TEXT = """
    1  : continuing
    1n : renaming
    1v : versioning
    1o : opening
    1c : recovering
    1l : opening latest
    1p : copy and move
    1r : registering courses
    2  : creating new versioning collection
    2q : query versioning info
    2c : clear versioning data
    3  : creating new capsule
    3i : initialization with conversation
    3r : initialization with registration
    4  : settings
"""

_MODE_OPTIONS = [
    "1  : continuation",
    "1n : continuation + rename",
    "1v : continuation + versioning",
    "1o : open file",
    "1c : recover version",
    "1l : open latest",
    "1p : copy and move",
    "1r : register course",
    "2  : new versioning collection",
    "2q : query versioning",
    "2c : clear versioning",
    "3  : new capsule",
    "3i : init with conversation",
    "3r : init with registration",
    "4  : settings",
]


# ── UI ヘルパー ────────────────────────────────────────────

def _read_key() -> bytes:
    """1キー分のバイト列を raw モードで読み取る（エスケープシーケンス含む）。"""
    ch = sys.stdin.buffer.read(1)
    if ch == b"\x1b":
        nxt = sys.stdin.buffer.read(1)
        if nxt == b"[":
            nxt2 = sys.stdin.buffer.read(1)
            return b"\x1b[" + nxt2
        return b"\x1b" + nxt
    return ch


def ui_select(question: str, options: list[str], extra_options: list[str] | None = None) -> str | None:
    """
    同一ターミナル上で矢印キー選択 + 直接文字入力の両対応。
    - 矢印キーでカーソル移動 → Enter で確定
    - 文字を入力すると typed に蓄積 → Enter で入力文字列をそのまま返す
    - Backspace で1文字削除
    - Ctrl-C でキャンセル（None を返す）
    """
    all_options = options + (extra_options or [])
    idx = 0
    typed = ""

    def render() -> int:
        lines = []
        lines.append(f"\033[1m{question}\033[0m")
        if typed:
            lines.append(f"  \033[33minput: {typed}\033[0m")
        for i, opt in enumerate(all_options):
            if i == idx and not typed:
                lines.append(f"  \033[36m> {opt}\033[0m")
            else:
                lines.append(f"    {opt}")
        sys.stdout.write("\r\n".join(lines) + "\r\n")
        sys.stdout.flush()
        return len(lines)

    def clear(n: int) -> None:
        sys.stdout.write(f"\033[{n}A\033[J")
        sys.stdout.flush()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    line_count = render()
    result = None
    cancelled = False

    try:
        tty.setraw(fd)
        while True:
            ch = _read_key()
            if ch == b"\x03":               # Ctrl-C
                cancelled = True
                break
            elif ch == b"\x1b[A":           # 上矢印
                typed = ""
                idx = (idx - 1) % len(all_options)
            elif ch == b"\x1b[B":           # 下矢印
                typed = ""
                idx = (idx + 1) % len(all_options)
            elif ch in (b"\r", b"\n"):      # Enter
                break
            elif ch in (b"\x7f", b"\x08"): # Backspace
                typed = typed[:-1]
            else:
                try:
                    typed += ch.decode("utf-8")
                except UnicodeDecodeError:
                    pass
            clear(line_count)
            line_count = render()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    clear(line_count)
    if cancelled:
        return None
    if typed:
        print(f"  > {typed}")
        return typed
    result = all_options[idx]
    print(f"  > {result}")
    return result


def ui_input(question: str, default: str = "") -> str | None:
    """
    同一ターミナル上でテキスト入力。
    ddによるペーストも正しく受け取る。Ctrl-C で None を返す。
    """
    sys.stdout.write(f"{question} {default}")
    sys.stdout.flush()
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return None
    result = (default + line).rstrip("\n").rstrip("\r") if default else line.rstrip("\n").rstrip("\r")
    return result


def ui_confirm(question: str) -> bool:
    """y/N をインラインで確認。デフォルトは No。"""
    ans = ui_input(f"{question} (y/N):")
    if ans is None:
        return False
    return ans.strip().lower() == "y"


# ── メインクラス ───────────────────────────────────────────

class MyAssignment:
    def __init__(self):
        self.my_path = Path(__file__).resolve()
        self.current_dir = Path(__file__).resolve().parent
        self.meta_data_path = self.current_dir / "myassi_meta.json"
        try:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                self.meta_data_json = json.load(f)
        except Exception:
            print("No valid assignment folder is set")
            print("Please set a valid folder before using")
            return
        app_cfg = self.meta_data_json.get("app_config", {})
        if app_cfg.get("show_course_today") is True:
            self.show_course_today()

    # ── 内部ユーティリティ ─────────────────────────────────

    def _save_meta(self) -> None:
        with open(self.meta_data_path, "w", encoding="utf-8") as f:
            json.dump(self.meta_data_json, f, ensure_ascii=False, indent=3)

    def _versioning_dir(self, capsule_name: str) -> Path:
        capsule_real_name = self.meta_data_json[capsule_name]["capsule_name"]
        root = Path(self.meta_data_json[capsule_name]["assi_folder_dir"])
        return root / f"{capsule_real_name}_versioning"

    def _load_versioning_meta(self, capsule_name: str) -> dict | None:
        path = self._versioning_dir(capsule_name) / "versioning_meta_data.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_versioning_meta(self, capsule_name: str, data: dict) -> None:
        path = self._versioning_dir(capsule_name) / "versioning_meta_data.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=3)

    # ── カプセル選択 ───────────────────────────────────────

    def ask_capsule_name(self) -> str | None:
        if len(self.meta_data_json) == 1:
            return "default"
        capsule_list = [k for k in self.meta_data_json if k != "app_config"]
        if len(capsule_list) == 1:
            return capsule_list[0]
        chosen = ui_select("Select a capsule:", capsule_list)
        if not chosen or chosen not in self.meta_data_json:
            return "default"
        return chosen

    # ── フォルダ掘り下げ ───────────────────────────────────

    def diving(self, searching_folder_dir_input, is_search_for_file: bool = False) -> Path:
        searching_folder_dir = Path(searching_folder_dir_input)
        if not is_search_for_file:
            target_names = [f.name for f in searching_folder_dir.iterdir() if f.is_dir()]
        else:
            target_names = [f.name for f in searching_folder_dir.iterdir()]

        extra = ["Add new folder", "[t] Stay here / terminate diving"]
        chosen = ui_select(
            f"Current: {searching_folder_dir}\nSelect a folder:",
            target_names,
            extra_options=extra,
        )

        if chosen is None or chosen == extra[1]:
            return searching_folder_dir

        if chosen == extra[0]:
            target_name_to_add = ui_input("Input the folder name to add:")
            if not target_name_to_add:
                return searching_folder_dir
            if "_" in target_name_to_add:
                parts = target_name_to_add.split("_")
                parent_name, child_name = parts[0], parts[-1]
                matches = [n for n in target_names if n == parent_name]
                new_dir = (
                    searching_folder_dir / matches[0] / child_name
                    if matches
                    else searching_folder_dir / target_name_to_add
                )
            else:
                new_dir = searching_folder_dir / target_name_to_add
            new_dir.mkdir(parents=True, exist_ok=True)
            return new_dir

        return searching_folder_dir / chosen

    # ── 今日のコース表示 ───────────────────────────────────

    def show_course_today(self) -> None:
        today = str(datetime.datetime.today().isoweekday())
        default_info = self.meta_data_json.get("default", {})
        registered = default_info.get("registered_courses")
        if registered and today in registered:
            print("Today's courses : ")
            for lesson, course_info in registered[today].items():
                if course_info["course_name"] is not None:
                    print(f"Lesson {lesson} : {course_info['course_name']}")
        else:
            print("No course registered for today")
        print()

    # ── ヘルプ ─────────────────────────────────────────────

    def help(self) -> None:
        print(_HELP_TEXT)

    # ── バージョニング操作 ─────────────────────────────────

    def set_versioning_mode(
        self,
        capsule_name: str | None = None,
        is_query: bool = False,
        is_clear: bool = False,
    ) -> None:
        if is_query:
            self._query_version(capsule_name)
        elif is_clear:
            self._clear_versioning_collection()
        else:
            self._create_versioning_collection(capsule_name)

    def _create_versioning_collection(self, capsule_name: str | None) -> None:
        meta = self.meta_data_json
        target = self.ask_capsule_name() if capsule_name is None else capsule_name
        if not target:
            return
        capsule_real_name = meta[target]["capsule_name"]
        capsule_root = Path(meta[target]["assi_folder_dir"])
        versioning_dir = self._versioning_dir(target)
        versioning_dir.mkdir(parents=True, exist_ok=True)

        dive_layer = meta[target]["config"]["dive_layer"]
        if meta[target]["config"]["use_weekday"]:
            dive_layer += 1

        searching_folder_dir: Path = capsule_root
        for _ in range(dive_layer):
            prev = searching_folder_dir
            searching_folder_dir = self.diving(searching_folder_dir)
            if prev == searching_folder_dir:
                break

        target_file_names = [f.name for f in searching_folder_dir.iterdir()]
        if not target_file_names:
            print("No files found in the selected folder.")
            return
        selected_name = ui_select("Select a file:", target_file_names)
        if not selected_name:
            return
        selected_path = searching_folder_dir / selected_name

        comment_raw = ui_input("Input comments (leave blank for none):")
        comment = comment_raw.strip() if comment_raw and comment_raw.strip() else None

        versioning_meta_path = versioning_dir / "versioning_meta_data.json"
        versioning_meta: dict = {}
        if versioning_meta_path.exists():
            with open(versioning_meta_path, "r", encoding="utf-8") as f:
                versioning_meta = json.load(f)

        default_alias = f"{capsule_real_name}_{datetime.datetime.now()}"
        alias_raw = ui_input("Name this versioning collection:", default=default_alias)
        alias = alias_raw.strip() if alias_raw and alias_raw.strip() else default_alias

        versioning_meta[alias] = {
            "active_path": str(selected_path),
            1: {
                "original_path": str(selected_path),
                "added_datetime": str(datetime.datetime.now()),
                "versioned_datetime": str(datetime.datetime.now()),
                "comments": comment,
            },
        }
        with open(versioning_meta_path, "w", encoding="utf-8") as f:
            json.dump(versioning_meta, f, ensure_ascii=False, indent=3)
        print(f"Successfully set up versioning collection : {alias}")

    def _clear_versioning_collection(self) -> None:
        target = self.ask_capsule_name()
        if not target:
            return
        versioning_meta = self._load_versioning_meta(target)
        if versioning_meta is None:
            print("No versioning collection exists")
            return

        selected = ui_select("Select a versioning collection:", list(versioning_meta.keys()))
        if not selected:
            return

        if not ui_confirm(f"Clearing versioning collection {selected}. Confirm?"):
            print("Clearing action cancelled")
            return

        active_path = Path(versioning_meta[selected]["active_path"])
        for version_name, version_data in versioning_meta[selected].items():
            if str(version_name).isdigit() and "archived_path" in version_data:
                archived = Path(version_data["archived_path"])
                if archived.exists() and archived != active_path:
                    os.unlink(archived)
        del versioning_meta[selected]
        self._save_versioning_meta(target, versioning_meta)
        print(f"Successfully cleared versioning collection : {selected}")

    def _query_version(self, capsule_name: str | None) -> None:
        searching_words_raw = ui_input("Search (keyword_option1_option2 ...):")
        if searching_words_raw is None:
            return
        parts = searching_words_raw.strip().split("_")
        keyword = parts[0]
        search_options = parts[1:]

        target = self.ask_capsule_name() if capsule_name is None else capsule_name
        if not target:
            return
        versioning_meta = self._load_versioning_meta(target)
        if not versioning_meta:
            print("No versioning data found")
            return

        matched = False
        for collection, collection_data in versioning_meta.items():
            if keyword and keyword.lower() not in str(collection).lower():
                continue
            matched = True
            print(f"{collection} : ")
            for version, version_data in collection_data.items():
                if version == "active_path":
                    print(f"Active path : {collection_data['active_path']}")
                else:
                    print(f"Version {version} : ")
                    for data_item, data_val in version_data.items():
                        if search_options:
                            if any(opt.lower() in str(data_item).lower() for opt in search_options):
                                print(f"   {data_item} : {data_val}")
                        else:
                            print(f"   {data_item} : {data_val}")
            print("-----")
        if not matched:
            print("No matching versioning collection")

    # ── コース登録補助 ─────────────────────────────────────

    def add_register_course(self) -> None:
        capsule_name = self.ask_capsule_name()
        if not capsule_name:
            return
        meta = self.meta_data_json
        registered = meta[capsule_name].get("registered_courses")
        if not registered:
            print("No registered courses found for this capsule")
            print("Redirecting to course registration ...")
            self.register_course()
            return

        while True:
            raw = ui_input("Input the lesson you want to register (e.g. 2-3 for Tuesday's 3rd lesson):")
            if raw is None:
                return
            raw = raw.strip()
            if re.match(r"\d+-\d+", raw):
                break
            print("Invalid input")

        day, period = raw.split("-")[0], raw.split("-")[1]
        if day not in registered:
            print("Invalid day of week")
            return
        if period not in registered[day]:
            print("Invalid lesson period")
            return

        course_info_raw = ui_input(
            'Input course information in the format of "course name, course credit, course category"\n→'
        )
        if course_info_raw is None:
            return
        parts = course_info_raw.split(",")
        course_name = course_credit = course_catagory = None
        try:
            course_name = parts[0].strip() or None
            course_credit = parts[1].strip()
            course_catagory = parts[2].strip()
        except (IndexError, AttributeError):
            pass

        assi_root = Path(meta[capsule_name]["assi_folder_dir"])
        day_folder = assi_root / DAY_OF_WEEK_REF[day]
        original = registered[day][period]

        if original["course_name"] is not None:
            print(
                "Warning : There is already a registered course for the designated lesson : \n"
                f"{original['course_name']}, {original['course_credit']}, {original['course_catagory']}"
            )
            if not ui_confirm("Do you want to overwrite the existing course information?"):
                print("Course registration cancelled")
                return
            os.rename(
                day_folder / f"{period}限：{original['course_name']}",
                day_folder / f"Original_{period}限：{original['course_name']}",
            )
            os.makedirs(day_folder / f"{period}限：{course_name}", exist_ok=True)
        elif course_name is None:
            os.rename(
                day_folder / f"{period}限：{original['course_name']}",
                day_folder / f"Original_{period}限：{original['course_name']}",
            )
        else:
            os.makedirs(day_folder / f"{period}限：{course_name}", exist_ok=True)

        meta[capsule_name]["registered_courses"][day][period] = {
            "course_name": course_name,
            "course_credit": course_credit,
            "course_catagory": course_catagory,
        }
        self._save_meta()
        print("Successfully registered course")

    def _register_assignment(self) -> None: 
        deadline = ui_input("Input the deadline for this assignment (e.g. 202412312359 for 2024-12-31 23:59):")
        deadline = str(deadline).strip()
        if not re.match(r"\d{12}", deadline):
            print("Invalid deadline format")
            return
        deadline_dt = datetime.datetime.strptime(deadline, "%Y%m%d%H%M")
        assi_name = ui_input("Input the name for this assignment:")
        assi_name = str(assi_name).strip()
        if not assi_name:
            print("Invalid assignment name")
            return
        print(f"Confirmation : Assignment - {assi_name}, Deadline - {deadline_dt}")
        confirmed = ui_confirm("Confirm registering this assignment?(y/N)")
        if confirmed not in ["N", "n"]:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["schedule"] = {deadline: assi_name}
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=3)
            print("Assignment registered")

    # ── continuation モード ────────────────────────────────

    def continuation_mode(
        self,
        is_renaming: bool = False,
        versioning: bool = False,
        is_open: bool = False,
        recover_version: bool = False,
        open_latest: bool = False,
        copy_and_move: bool = False,
        register_course: bool = False,
        register_assignment: bool = False,
    ) -> None:
        meta = self.meta_data_json
        if len(meta) == 1:
            print("No default assignment folder is set")
            print("Please set default folder before using")
            return

        if not open_latest:
            used_capsule_name = self.ask_capsule_name()
            if not used_capsule_name:
                return
        else:
            used_capsule_name = "default"

        if is_open:
            self._open_file(meta, used_capsule_name)
        elif open_latest:
            self._open_latest_file(meta)
        elif recover_version:
            self._version_file(meta, used_capsule_name, is_recovering=True)
        elif register_course:
            self.add_register_course()
        elif register_assignment:
            self._register_assignment()
        else:
            your_assi_path = ui_input("Drag your assignment here (paste the path):")
            if not your_assi_path:
                return
            your_assi_path = your_assi_path.strip()
            renamed_name = ""
            if is_renaming:
                r = ui_input("Rename as:")
                renamed_name = r.strip() if r else ""

            if not versioning:
                result_path = self._move_file(meta, used_capsule_name, your_assi_path, renamed_name, copy_and_move)
            else:
                result_path = self._version_file(meta, used_capsule_name, file_str=your_assi_path, renamed_name=renamed_name)

            meta["app_config"]["latest_opened"] = result_path
            self._save_meta()

    def _move_file(
        self,
        meta: dict,
        capsule_name: str,
        file_str: str,
        renamed_name: str,
        copy_and_move: bool,
    ) -> str | None:
        file = Path(file_str)
        print(f"Processing : {file}")
        capsule_root = Path(meta[capsule_name]["assi_folder_dir"])
        cfg = meta[capsule_name]["config"]

        if cfg["use_weekday"]:
            allowed = ["1", "2", "3", "4", "5"]
            if cfg["include_weekends"]:
                allowed += ["6", "7"]
            day_options = [f"{d} : {DAY_OF_WEEK_REF_ENG[d]} ({DAY_OF_WEEK_REF[d]})" for d in allowed]
            chosen_day = ui_select("Day of week of the lesson:", day_options)
            if not chosen_day:
                return None
            day_key = chosen_day.split(" : ")[0]
            searching_folder_dir = capsule_root / DAY_OF_WEEK_REF[day_key]
            searching_folder_dir.mkdir(parents=True, exist_ok=True)
        else:
            searching_folder_dir = capsule_root

        for _ in range(cfg["dive_layer"]):
            prev = searching_folder_dir
            searching_folder_dir = self.diving(searching_folder_dir)
            if prev == searching_folder_dir:
                break

        file_name = f"{renamed_name}{file.suffix}" if renamed_name else file.name
        destination = searching_folder_dir / file_name

        print("-----")
        print(f"original path : {file}")

        if destination.exists():
            print(destination)
            print("This file name already exists.")
            conflict_options = [
                "0 : Auto-resolve (default)",
                "1 : Stop moving",
                "2 : Rename it",
                "3 : Do a versioning",
                "4 : Overwrite the existing one",
            ]
            reaction_str = ui_select("How do you want to handle it?", conflict_options)
            if not reaction_str:
                return None
            reaction = int(reaction_str[0])

            if reaction == 0:
                idx = 1
                stem, ext = file.stem, file.suffix
                while destination.exists():
                    destination = searching_folder_dir / f"{stem}_{idx}{ext}"
                    idx += 1
            elif reaction == 1:
                print("Moving action interrupted")
                return None
            elif reaction == 2:
                new_name = ui_input("Rename:")
                if not new_name or not new_name.strip():
                    print("Moving action interrupted")
                    return None
                destination = searching_folder_dir / f"{new_name.strip()}{file.suffix}"
                if destination.exists():
                    print("This file name also exists")
                    print("Moving action interrupted")
                    return None
            elif reaction == 3:
                print("Please restart and select the versioning mode")
                return None
            elif reaction == 4:
                pass

        if copy_and_move:
            shutil.copy2(file, destination)
        else:
            shutil.move(file, destination)
        print(f"Moved to {destination}")
        print("Successful")
        return str(destination)

    def _version_file(
        self,
        meta: dict,
        capsule_name: str,
        file_str: str | None = None,
        renamed_name: str | None = None,
        is_recovering: bool = False,
    ) -> str | None:
        capsule_root = Path(meta[capsule_name]["assi_folder_dir"])
        capsule_real_name = meta[capsule_name]["capsule_name"]
        version_dir = capsule_root / f"{capsule_real_name}_versioning"
        versioning_meta = self._load_versioning_meta(capsule_name)

        if versioning_meta is None:
            print("No versioning collection exists")
            print("Please create a versioning collection")
            self.set_versioning_mode(capsule_name=capsule_name)
            return None

        selected = ui_select(
            "Select a versioning collection:",
            list(versioning_meta.keys()),
            extra_options=["No desired versioning collection"],
        )
        if not selected:
            return None
        if selected == "No desired versioning collection":
            print("Redirect to set versioning mode")
            self.set_versioning_mode(capsule_name=capsule_name)
            return None

        active_path = Path(versioning_meta[selected]["active_path"])

        version_to_recover = None
        if is_recovering:
            version_keys = [k for k in versioning_meta[selected] if k != "active_path"]
            version_to_recover = ui_select("Select a version to recover:", [str(k) for k in version_keys])
            if not version_to_recover:
                return None
            if version_to_recover not in versioning_meta[selected]:
                print("The designated version does not exist")
                return None

        comment_raw = ui_input("Input comments (leave blank for none):")
        comment = comment_raw.strip() if comment_raw and comment_raw.strip() else None

        version_num = len(versioning_meta[selected]) - 1
        archive_file_name = f"{active_path.stem}_ver{version_num}{active_path.suffix}"
        archived_path = version_dir / archive_file_name
        shutil.move(active_path, archived_path)

        if is_recovering:
            recover_meta = versioning_meta[selected][version_to_recover]
            recover_path = Path(recover_meta["archived_path"])
            storing_path = active_path.parent / recover_path.name
            shutil.move(recover_path, storing_path)
        else:
            src = Path(file_str)
            storing_name = f"{renamed_name}{src.suffix}" if renamed_name else src.name
            storing_path = active_path.parent / storing_name
            shutil.move(src, storing_path)

        versioning_meta[selected]["active_path"] = str(storing_path)
        v_data = versioning_meta[selected][str(version_num)]
        v_data["archived_path"] = str(archived_path)
        v_data["versioned_datetime"] = str(datetime.datetime.now())
        versioning_meta[selected][str(version_num)] = v_data
        versioning_meta[selected][str(version_num + 1)] = {
            "original_path": str(storing_path),
            "added_datetime": str(datetime.datetime.now()),
            "comments": comment,
        }
        if is_recovering:
            del versioning_meta[selected][version_to_recover]

        self._save_versioning_meta(capsule_name, versioning_meta)
        print("File versioned successfully")
        return str(storing_path)

    def _open_file(self, meta: dict, capsule_name: str) -> None:
        searching_folder_dir: Path | str = meta[capsule_name]["assi_folder_dir"]
        while True:
            prev = searching_folder_dir
            searching_folder_dir = self.diving(searching_folder_dir, is_search_for_file=True)
            if prev == searching_folder_dir:
                break
            if Path(searching_folder_dir).is_file():
                break
            if not ui_confirm("Proceed?"):
                break
        self._reveal_in_explorer(searching_folder_dir)

    def _open_latest_file(self, meta: dict) -> None:
        latest = meta.get("app_config", {}).get("latest_opened")
        if not latest:
            print("No latest opened file found")
            return
        path = Path(latest)
        if not path.exists():
            print("File not exist")
            return
        self._reveal_in_explorer(path)

    @staticmethod
    def _reveal_in_explorer(target) -> None:
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", "-R", str(target)])
        elif system == "Windows":
            subprocess.run(["explorer", "/select", str(target)])
        else:
            print("Only MacOS and Windows are supported currently")

    # ── コース初期登録 ─────────────────────────────────────

    def register_course(self) -> list | None:
        while True:
            raw = ui_input("Input number for lessons per day:")
            if raw is None:
                return None
            if raw.isdigit() and int(raw) >= 2:
                lesson_num = int(raw)
                break
            print("Please input a number larger than or equal to 2")

        registered_courses_info: dict = {}
        print('Please input the course information for the lessons in the format of "course name, course credit, course category"')
        print("If there is no course for the lesson, just press enter")

        for day in range(1, 6):
            print("----------")
            print(DAY_OF_WEEK_REF_ENG[str(day)])
            day_course_info: dict = {}
            for lesson in range(1, lesson_num + 1):
                raw_info = ui_input(f"Lesson {lesson} :") or ""
                parts = raw_info.split(",")
                course_name = course_credit = course_catagory = None
                try:
                    course_name = parts[0].strip() or None
                    course_credit = parts[1].strip()
                    course_catagory = parts[2].strip()
                except (IndexError, AttributeError):
                    pass
                day_course_info[str(lesson)] = {
                    "course_name": course_name,
                    "course_credit": course_credit,
                    "course_catagory": course_catagory,
                }
            registered_courses_info[str(day)] = day_course_info

        print("---------")
        print("Confirmation of registered courses : ")
        for day, lessons in registered_courses_info.items():
            print(DAY_OF_WEEK_REF_ENG[day])
            for lesson, info in lessons.items():
                print(f"Lesson {lesson} : {info['course_name']}, {info['course_credit']}, {info['course_catagory']}")
        print("---------")
        if not ui_confirm("Confirm registered courses?"):
            print("Course registration cancelled")
            return None

        while True:
            sem_name = ui_input("Input semester name:")
            if sem_name and sem_name.strip():
                sem_name = sem_name.strip()
                break
            print("Please input a valid semester name")

        is_confirmed = False
        while not is_confirmed:
            new_sem_dir = ui_input("Input a directory for the semester:")
            if not new_sem_dir:
                return None
            new_sem_dir = new_sem_dir.strip()
            if Path(new_sem_dir).is_dir():
                print(f"Confirmation : {new_sem_dir}")
                is_confirmed = ui_confirm("Please confirm the directory for your new semester")
            else:
                print("The designated is a file path instead of a directory.")
                if ui_confirm("Use the parent directory of your designated file path for your new semester?"):
                    is_confirmed = True
                    new_sem_dir = str(Path(new_sem_dir).resolve().parent)

        if not Path(new_sem_dir).exists:
            os.makedirs(new_sem_dir, exist_ok=True)

        print("Building assignment directory ...")
        os.mkdir(Path(new_sem_dir) / sem_name)
        for day, lessons in registered_courses_info.items():
            day_folder = Path(new_sem_dir) / sem_name / DAY_OF_WEEK_REF[day]
            day_folder.mkdir(parents=True, exist_ok=True)
            for lesson, info in lessons.items():
                if info["course_name"] is not None:
                    (day_folder / f"{lesson}限：{info['course_name']}").mkdir(parents=True, exist_ok=True)

        print("Successfully registered courses and built assignment directory")
        return [str(Path(new_sem_dir) / sem_name), registered_courses_info]

    # ── 初期化モード ───────────────────────────────────────

    def initialization_mode(
        self, config_conversation: bool = False, init_with_reg: bool = False
    ) -> None:
        if init_with_reg:
            course_info = self.register_course()
            if not course_info:
                return
            new_folder_dir, register_course_info = course_info
        else:
            print("Create new assignment capsule here")
            is_confirmed = False
            while not is_confirmed:
                new_folder_dir = ui_input("Input a directory for your new assignment folder:")
                if not new_folder_dir:
                    return
                new_folder_dir = new_folder_dir.strip()
                if Path(new_folder_dir).is_dir():
                    print(f"Confirmation : {new_folder_dir}")
                    is_confirmed = ui_confirm("Please confirm the directory of your new assignment folder")
                else:
                    print("The designated is a file path instead of a directory.")
                    if ui_confirm("Use the parent directory of your designated file path as your assignment directory?"):
                        is_confirmed = True
                        new_folder_dir = str(Path(new_folder_dir).resolve().parent)
            if not Path(new_folder_dir).exists:
                os.makedirs(new_folder_dir, exist_ok=True)
            register_course_info = None

        capsule_name = ui_input("Input your new capsule name:")
        if not capsule_name:
            return
        capsule_name = capsule_name.strip()

        cfg = dict(CONFIG)
        if config_conversation:
            cfg["use_weekday"] = ui_confirm("Use the weekday based allocation system?")
            cfg["include_weekends"] = ui_confirm("Include weekends in your file system?")
            dl_raw = ui_input("Designate the number of dive layers:")
            cfg["dive_layer"] = int(dl_raw) if (dl_raw and dl_raw.isdigit()) else 1

        meta_data_raw = {
            "assi_folder_dir": new_folder_dir,
            "capsule_name": capsule_name,
            "config": cfg,
            "registered_courses": register_course_info if init_with_reg else None,
        }

        meta = self.meta_data_json
        if len(meta) == 1:
            meta["default"] = meta_data_raw
            self._save_meta()
        else:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            while capsule_name in meta:
                print("Capsule name already exists")
                capsule_name = ui_input("Input your new capsule name:")
                if not capsule_name:
                    return
                capsule_name = capsule_name.strip()
            meta_data_raw["capsule_name"] = capsule_name

            if ui_confirm("Make to default?"):
                current_default = meta["default"]
                meta[current_default["capsule_name"]] = current_default
                meta["default"] = meta_data_raw
            else:
                meta[capsule_name] = meta_data_raw

            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=3)

        print("New capsule created")
        print(f"capsule name : {capsule_name}")
        print(f"assignment folder directory : {new_folder_dir}")

    # ── 設定モード ─────────────────────────────────────────

    def settings_mode(self) -> None:
        SETTING_ITEMS = {
            "1": "change default",
            "2": "change assignment folder",
            "3": "edit configurations",
            "4": "edit app configurations",
            "5": "update",
        }
        meta = self.meta_data_json
        chosen = ui_select("Choose a setting item:", [f"{k} : {v}" for k, v in SETTING_ITEMS.items()])
        if not chosen:
            return
        item = chosen.split(" : ")[0]

        if item in ("1", "2") and len(meta) == 1:
            print("There is no capsule to set")
            return

        if item == "1":
            if len(meta) == 2:
                print("There is only one capsule which is already in default")
                return
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            if setting_capsule_name == "default":
                print("The selected capsule is already in default")
                return
            current_default_real = meta["default"]["capsule_name"]
            meta[current_default_real] = meta["default"]
            meta["default"] = meta[setting_capsule_name]
            del meta[setting_capsule_name]
            self._save_meta()
            print(f"Successfully set {setting_capsule_name} to default")

        elif item == "2":
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            is_confirmed = False
            while not is_confirmed:
                new_dir = ui_input("Input the new directory for your assignment folder:")
                if not new_dir:
                    return
                new_dir = new_dir.strip()
                if Path(new_dir).is_dir():
                    print(f"Confirmation : {new_dir}")
                    is_confirmed = ui_confirm("Please confirm the directory of your new assignment folder")
                else:
                    print("The designated is a file path instead of a directory.")
                    if ui_confirm("Use the parent directory of your designated file path as your assignment directory?"):
                        is_confirmed = True
                        new_dir = str(Path(new_dir).resolve().parent)
            original_root = Path(meta[setting_capsule_name]["assi_folder_dir"])
            versioning_folder = original_root / f"{meta[setting_capsule_name]['capsule_name']}_versioning"
            meta[setting_capsule_name]["assi_folder_dir"] = new_dir
            if versioning_folder.exists():
                shutil.move(versioning_folder, Path(new_dir))
            print(f"Successfully changed to : {new_dir}")

        elif item == "3":
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            config_items = list(CONFIG_CONVENTION.keys())
            is_continue = True
            while is_continue:
                print("Current Settings:")
                config_options = []
                for config_item in config_items:
                    orig = meta[setting_capsule_name]["config"][config_item]
                    label = f"{config_item} ({CONFIG_CONVENTION[config_item]}) - {orig}"
                    print(f"  {label}")
                    config_options.append(label)

                chosen_cfg = ui_select("Select item to edit:", config_options)
                if not chosen_cfg:
                    break
                key = config_items[config_options.index(chosen_cfg)]
                orig_val = meta[setting_capsule_name]["config"][key]

                if isinstance(orig_val, bool):
                    if ui_confirm(f"Switch {key} from {orig_val} to {not orig_val}?"):
                        meta[setting_capsule_name]["config"][key] = not orig_val
                elif isinstance(orig_val, int):
                    new_val_str = ui_input(f"Designate new value for {key}:", default=str(orig_val))
                    meta[setting_capsule_name]["config"][key] = (
                        int(new_val_str) if (new_val_str and new_val_str.isdigit()) else orig_val
                    )
                is_continue = ui_confirm("Edit other settings?")

            print("Current Settings:")
            for config_item in config_items:
                print(f"{config_item} ({CONFIG_CONVENTION[config_item]}) - {meta[setting_capsule_name]['config'][config_item]}")
            self._save_meta()

        elif item == "4":
            app_cfg = meta.get("app_config", {})
            bool_items = [k for k, v in app_cfg.items() if isinstance(v, bool)]
            if not bool_items:
                print("No configurable app settings found")
                return
            is_continue = True
            while is_continue:
                print("Current app configurations : ")
                app_options = [f"{k} - {app_cfg[k]}" for k in bool_items]
                for opt in app_options:
                    print(f"  {opt}")
                chosen_app = ui_select("Select item to toggle:", app_options)
                if not chosen_app:
                    break
                key = bool_items[app_options.index(chosen_app)]
                app_cfg[key] = not app_cfg[key]
                is_continue = ui_confirm("Edit other app configurations?")
            self._save_meta()
            print("Current app configurations : ")
            for k in bool_items:
                print(f"{k} - {app_cfg[k]}")

        elif item == "5":
            try:
                from updater import update_from_git
            except ImportError:
                print("Unable to obtain the updater script")
                return
            update_from_git(self.current_dir, self.my_path)
            exit()

        else:
            print("Invalid")


# ── エントリーポイント ─────────────────────────────────────

def main() -> None:
    print("Welcome to MyAssignment\n")
    ma = MyAssignment()

    chosen = ui_select("MyAssignment — Select a mode (or type directly e.g. 1v):", _MODE_OPTIONS)
    if chosen is None:
        print("Cancelled.")
        return

    mode = chosen.split(" : ")[0].strip() if " : " in chosen else chosen.strip()
    print()

    if not re.fullmatch(r"\d[a-zA-Z]?", mode):
        print("Invalid mode")
        return

    digit = mode[0]
    if digit == "1":
        ma.continuation_mode(
            is_renaming="n" in mode,
            versioning="v" in mode,
            is_open="o" in mode,
            recover_version="c" in mode,
            open_latest="l" in mode,
            copy_and_move="p" in mode,
            register_course="r" in mode,
            register_assignment="a" in mode,
        )
    elif digit == "2":
        ma.set_versioning_mode(is_query="q" in mode, is_clear="c" in mode)
    elif digit == "3":
        ma.initialization_mode(config_conversation="i" in mode, init_with_reg="r" in mode)
    elif digit == "4":
        ma.settings_mode()
    else:
        print("Invalid mode")

    print()


if __name__ == "__main__":
    main()

# cd /Users/shiinaayame/Documents/Daily_tools/assignment_allocator ; python3 submitter.py
"""
TODOS:
1 in initialization, confirm no files are set to client folder *
2 avoid user from choosing app config which is not a capsule name  *
3 allow users to choose to copy and move *
4 allow users to terminate diving *
5 strengthen mode input check (now, for eg cat1 will also be treated as 1 and c in mode) *
6 the capsulename_versioning folder is not a normal folder so hide it in menu *
7 Space is accidentally added to the collection dir name when setting
8 allow users to alter names of folders and files without crashing the app
9 Allow users to directly operate versioning collections after query

TODOS:
10 add options to app_config to improve usability
11 fix and update setting items 1 , 2 , 3 *
"""