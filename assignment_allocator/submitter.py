from pathlib import Path
import json
import shutil
import os
import re
import sys
import datetime
import subprocess
import platform

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

# ── UI ヘルパー ────────────────────────────────────────────

def help(self):
    info = ("""
            1 : continuing
            1n : renaming
            1v : versioning
            1o : opening
            1c : recovering
            1l : opening latest
            1p : copy and move
            1r : registering courses
            2 : creating new versioning collection
            2q : query versioning info
            2c : clear versioning data
            3 : creating new capsule
            3i : initialization with conversation
            3r : initialization with registrastion
            4 : settings
            """)
    print(info)


def ui_select(question: str, options: list[str], extra_options: list[str] | None = None) -> str | None:
    """
    ターミナルインラインで矢印キー選択 + 直接文字入力の両対応。
    - 矢印キーでカーソル移動 → Enter で確定
    - 文字を入力すると typed_input に蓄積 → Enter で入力文字列をそのまま返す
    - Backspace で1文字削除
    - Ctrl-C でキャンセル（None を返す）
    """
    all_options = options + (extra_options or [])
    state = {"idx": 0, "cancelled": False, "typed": ""}

    def get_tokens():
        tokens = []
        tokens.append(("bold", question + "\n"))
        if state["typed"]:
            tokens.append(("ansiyellow", f"  input: {state['typed']}\n"))
        for i, opt in enumerate(all_options):
            if i == state["idx"] and not state["typed"]:
                tokens.append(("ansicyan", f"  ❯ {opt}\n"))
            else:
                tokens.append(("", f"    {opt}\n"))
        return tokens

    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        state["typed"] = ""
        state["idx"] = (state["idx"] - 1) % len(all_options)

    @kb.add("down")
    def _down(event):
        state["typed"] = ""
        state["idx"] = (state["idx"] + 1) % len(all_options)

    @kb.add("backspace")
    def _backspace(event):
        state["typed"] = state["typed"][:-1]

    @kb.add("enter")
    def _enter(event):
        event.app.exit()

    @kb.add("c-c")
    def _cancel(event):
        state["cancelled"] = True
        event.app.exit()

    # 印字可能文字はすべて typed に蓄積
    @kb.add("<any>")
    def _any(event):
        ch = event.key_sequence[0].key
        if len(ch) == 1 and ch.isprintable():
            state["typed"] += ch

    app = Application(
        layout=Layout(Window(content=FormattedTextControl(get_tokens, focusable=True))),
        key_bindings=kb,
        full_screen=False,
        mouse_support=False,
    )
    app.run()

    if state["cancelled"]:
        return None
    if state["typed"]:
        print(f"  ❯ {state['typed']}")
        return state["typed"]
    chosen = all_options[state["idx"]]
    print(f"  ❯ {chosen}")
    return chosen


def ui_input(question: str, default: str = "") -> str | None:
    """
    prompt_toolkit の prompt() でテキスト入力。
    Ctrl-C で None を返す。
    """
    try:
        result = prompt(f"{question} ", default=default)
        return result
    except KeyboardInterrupt:
        return None


def ui_confirm(question: str) -> bool:
    """
    y/N をインラインで確認。デフォルトは No。
    """
    try:
        ans = prompt(f"{question} (y/N): ")
        return ans.strip().lower() == "y"
    except KeyboardInterrupt:
        return False


# ── 定数 ──────────────────────────────────────────────────

print("Welcome to MyAssignment")
print(" ")

DAY_OF_WEEK_REF = {
    "1": "月", "2": "火", "3": "水", "4": "木",
    "5": "金", "6": "土", "7": "日"
}
DAY_OF_WEEK_REF_ENG = {
    "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu",
    "5": "Fri", "6": "Sat", "7": "Sun"
}
CONFIG = {
    "use_weekday": True,
    "include_weekends": False,
    "dive_layer": 1
}
CONFIG_CONVENTION = {
    "use_weekday": "Use the day-of-a-week based allocation system",
    "include_weekends": "Include weekends in your file system",
    "dive_layer": "The number of dive layers"
}


class MyAssignment:
    def __init__(self):
        self.my_path = Path(__file__).resolve()
        self.current_dir = Path(__file__).resolve().parent
        self.meta_data_path = self.current_dir / "myassi_meta.json"
        try:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                self.meta_data_json = json.load(f)
        except:
            print("No valid assignment folder is set")
            print("Please set a valid folder before using")
            return
        if "show_course_today" in self.meta_data_json["app_config"]:
            if self.meta_data_json["app_config"]["show_course_today"] == True:
                self.show_course_today()

    def ask_capsule_name(self):
        if len(self.meta_data_json) == 1:
            return "default"
        capsule_list = [k for k in self.meta_data_json if k != "app_config"]
        if len(capsule_list) == 1:
            return capsule_list[0]
        chosen = ui_select("Select a capsule:", capsule_list)
        return chosen if chosen else "default"

    def diving(self, searching_folder_dir_input, is_search_for_file=False):
        searching_folder_dir = Path(searching_folder_dir_input)
        if not is_search_for_file:
            target_names = [f.name for f in searching_folder_dir.iterdir() if f.is_dir()]
        else:
            target_names = [f.name for f in searching_folder_dir.iterdir()]

        extra = ["Add new folder", "[t] Stay here / terminate diving"]
        chosen = ui_select(
            f"Current: {searching_folder_dir}\nSelect a folder:",
            target_names,
            extra_options=extra
        )

        if chosen is None or chosen == extra[1]:
            return searching_folder_dir

        if chosen == extra[0]:
            target_name_to_add = ui_input("Input the folder name to add:")
            if not target_name_to_add:
                return searching_folder_dir
            if "_" in target_name_to_add:
                target_selected_break = target_name_to_add.split("_")
                parent_name = target_selected_break[0]
                child_name = target_selected_break[-1]
                matches = [n for n in target_names if n == parent_name]
                if matches:
                    new_dir = searching_folder_dir / matches[0] / child_name
                else:
                    new_dir = searching_folder_dir / target_name_to_add
            else:
                new_dir = searching_folder_dir / target_name_to_add
            new_dir.mkdir(parents=True, exist_ok=True)
            return new_dir

        return searching_folder_dir / chosen

    def show_course_today(self):
        today_day_of_week = str(datetime.datetime.today().isoweekday())
        defult_capsule_info = self.meta_data_json["default"]
        if "registered_courses" in defult_capsule_info and defult_capsule_info["registered_courses"] != None:
            registered_courses = defult_capsule_info["registered_courses"]
            if today_day_of_week in registered_courses:
                today_courses = registered_courses[today_day_of_week]
                print("Today's courses : ")
                for lesson in today_courses:
                    course_info = today_courses[lesson]
                    if course_info["course_name"] != None:
                        print(f"Lesson {lesson} : {course_info['course_name']}")
            else:
                print("No course registered for today")
        print(" ")

    def set_versioning_mode(self, capsule_name=None, is_query=False, is_clear=False):

        def set_version(capsule_name):
            meta_data_json = self.meta_data_json
            target_capsule_name = self.ask_capsule_name() if capsule_name is None else capsule_name
            if not target_capsule_name:
                return
            target_capsule_real_name = meta_data_json[target_capsule_name]["capsule_name"]
            capsule_root_folder_dir = meta_data_json[target_capsule_name]["assi_folder_dir"]
            versioning_dir = Path(capsule_root_folder_dir) / f"{target_capsule_real_name}_versioning"
            if not versioning_dir.exists():
                versioning_dir.mkdir(parents=True, exist_ok=True)

            dive_layer = meta_data_json[target_capsule_name]["config"]["dive_layer"]
            searching_layer = 1
            if meta_data_json[target_capsule_name]["config"]["use_weekday"] == True:
                dive_layer += 1
            searching_folder_dir = capsule_root_folder_dir
            while searching_layer <= dive_layer:
                before_searching_folder_dir = searching_folder_dir
                searching_folder_dir = self.diving(searching_folder_dir)
                if before_searching_folder_dir == searching_folder_dir:
                    break
                searching_layer += 1

            target_file_names = [f.name for f in Path(searching_folder_dir).iterdir()]
            if not target_file_names:
                print("No files found in the selected folder.")
                return
            target_selected_name = ui_select("Select a file:", target_file_names)
            if not target_selected_name:
                return
            target_selected_path = Path(searching_folder_dir) / target_selected_name

            comment = ui_input("Input comments (leave blank for none):")
            comment = None if (comment is None or comment.strip() == "") else comment.strip()

            versioning_meta_data_json_path = versioning_dir / "versioning_meta_data.json"
            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
            else:
                versioning_meta_data_json = {}

            default_alias = f"{target_capsule_real_name}_{datetime.datetime.now()}"
            versioning_collection_alias = ui_input("Name this versioning collection:", default=default_alias)
            if not versioning_collection_alias or versioning_collection_alias.strip() == "":
                versioning_collection_alias = default_alias
            else:
                versioning_collection_alias = versioning_collection_alias.strip()

            versioning_meta_data_json[versioning_collection_alias] = {
                "active_path": str(target_selected_path),
                1: {
                    "original_path": str(target_selected_path),
                    "added_datetime": str(datetime.datetime.now()),
                    "versioned_datetime": str(datetime.datetime.now()),
                    "comments": comment
                }
            }
            with open(versioning_meta_data_json_path, "w", encoding="utf-8") as f:
                json.dump(versioning_meta_data_json, f, ensure_ascii=False, indent=3)
            print(f"Successfully set up versioning collection : {versioning_collection_alias}")

        def clear_collection():
            target_capsule_name = self.ask_capsule_name()
            if not target_capsule_name:
                return
            capsule_root_folder_dir = Path(self.meta_data_json[target_capsule_name]["assi_folder_dir"])
            target_capsule_real_name = self.meta_data_json[target_capsule_name]["capsule_name"]
            version_dir = capsule_root_folder_dir / f"{target_capsule_real_name}_versioning"
            versioning_meta_data_json_path = version_dir / "versioning_meta_data.json"
            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
            else:
                print("No versioning collection exists")
                return

            versioning_collections = list(versioning_meta_data_json.keys())
            selected = ui_select("Select a versioning collection:", versioning_collections)
            if not selected:
                return
            selected_versioning_collection = selected

            confirmed = ui_confirm(f"Clearing versioning collection {selected_versioning_collection}. Confirm?")
            if not confirmed:
                print("Clearing action cancelled")
                return

            active_path = Path(versioning_meta_data_json[selected_versioning_collection]["active_path"])
            version_data = versioning_meta_data_json[selected_versioning_collection]
            for version_name in version_data:
                if str(version_name).isdigit() and "archived_path" in version_data[version_name]:
                    version_archive_path = Path(version_data[version_name]["archived_path"])
                    if version_archive_path.exists() and version_archive_path != active_path:
                        os.unlink(version_archive_path)
            del versioning_meta_data_json[selected_versioning_collection]
            with open(versioning_meta_data_json_path, "w", encoding="utf-8") as f:
                json.dump(versioning_meta_data_json, f, ensure_ascii=False, indent=3)
            print(f"Successfully cleared versioning collection : {selected_versioning_collection}")

        def query_version():
            searching_words_raw = ui_input("Search (keyword_option1_option2 ...):")
            if searching_words_raw is None:
                return
            searching_words = searching_words_raw.strip().split("_")
            keyword = searching_words[0]
            search_options = searching_words[1:] if len(searching_words) > 1 else []

            meta_data_json = self.meta_data_json
            target_capsule_name = self.ask_capsule_name() if capsule_name is None else capsule_name
            if not target_capsule_name:
                return
            capsule_root_folder_dir = meta_data_json[target_capsule_name]["assi_folder_dir"]
            target_capsule_real_name = meta_data_json[target_capsule_name]["capsule_name"]
            versioning_dir = Path(capsule_root_folder_dir) / f"{target_capsule_real_name}_versioning"
            versioning_meta_data_json_path = versioning_dir / "versioning_meta_data.json"

            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
                if versioning_meta_data_json == {}:
                    print("No versioning data found")
                    return

                is_have_something_matched_kw = False
                for versioning_collection in versioning_meta_data_json:
                    if keyword != "" and keyword.lower() not in str(versioning_collection).lower():
                        continue
                    is_have_something_matched_kw = True
                    print(f"{versioning_collection} : ")
                    collection_data = versioning_meta_data_json[versioning_collection]
                    for version in versioning_meta_data_json[versioning_collection]:
                        if version == "active_path":
                            print(f"Active path : {collection_data['active_path']}")
                        else:
                            print(f"Version {version} : ")
                            version_data = collection_data[version]
                            for data_item in version_data:
                                if search_options:
                                    for search_option in search_options:
                                        if search_option.lower() in str(data_item).lower():
                                            print(f"   {data_item} : {version_data[data_item]}")
                                            break
                                else:
                                    print(f"   {data_item} : {version_data[data_item]}")
                    print("-----")
                if not is_have_something_matched_kw:
                    print("No matching versioning collection")
            else:
                print("No versioning data found")

        if is_query:
            query_version()
        elif is_clear:
            clear_collection()
        else:
            set_version(capsule_name)

    def add_register_course(self):
        registering_capsule_name = self.ask_capsule_name()
        if not registering_capsule_name:
            return
        meta_data_json = self.meta_data_json
        if "registered_courses" not in meta_data_json[registering_capsule_name] or meta_data_json[registering_capsule_name]["registered_courses"] is None:
            print("No registered courses found for this capsule")
            print("Redirecting to course registration ...")
            self.register_course()
            return
        course_meta_data = meta_data_json[registering_capsule_name]["registered_courses"]

        while True:
            lesson_to_register = ui_input("Input the lesson you want to register (e.g. 2-3 for Tuesday's 3rd lesson):")
            if lesson_to_register is None:
                return
            lesson_to_register = lesson_to_register.strip()
            if re.match(r"\d+-\d+", lesson_to_register):
                break
            print("Invalid input")

        day_to_register = lesson_to_register.split("-")[0]
        period_to_register = lesson_to_register.split("-")[1]
        if day_to_register not in course_meta_data:
            print("Invalid day of week")
            return
        if period_to_register not in course_meta_data[day_to_register]:
            print("Invalid lesson period")
            return

        course_info = ui_input('Input course information in the format of "course name, course credit, course category"\n→')
        if course_info is None:
            return
        course_info_split = course_info.split(",")
        course_name, course_credit, course_catagory = None, None, None
        try:
            course_name = None if course_info_split[0].strip() == "" else course_info_split[0].strip()
            course_credit = course_info_split[1].strip()
            course_catagory = course_info_split[2].strip()
        except:
            pass

        original_course_info = course_meta_data[day_to_register][period_to_register]
        if original_course_info["course_name"] is not None:
            print("Warning : There is already a registered course for the designated lesson : "
                  f"\n{original_course_info['course_name']}, {original_course_info['course_credit']}, {original_course_info['course_catagory']}")
            confirmation = ui_confirm("Do you want to overwrite the existing course information?")
            if not confirmation:
                print("Course registration cancelled")
                return
            os.rename(
                Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"{period_to_register}限：{original_course_info['course_name']}",
                Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"Original_{period_to_register}限：{original_course_info['course_name']}"
            )
            os.makedirs(Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"{period_to_register}限：{course_name}", exist_ok=True)
        elif course_name is None:
            os.rename(
                Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"{period_to_register}限：{original_course_info['course_name']}",
                Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"Original_{period_to_register}限：{original_course_info['course_name']}"
            )
        else:
            os.makedirs(Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"{period_to_register}限：{course_name}", exist_ok=True)

        meta_data_json[registering_capsule_name]["registered_courses"][day_to_register][period_to_register] = {
            "course_name": course_name,
            "course_credit": course_credit,
            "course_catagory": course_catagory
        }
        with open(self.meta_data_path, "w", encoding="utf-8") as f:
            json.dump(meta_data_json, f, ensure_ascii=False, indent=3)
        print("Successfully registered course")

    def continuation_mode(
            self,
            is_renaming=False,
            versioning=False,
            is_open=False,
            recover_version=False,
            open_latest=False,
            copy_and_move=False,
            register_course=False
    ):
        meta_data_json = self.meta_data_json
        if len(meta_data_json) == 1:
            print("No default assignment folder is set")
            print("Please set default folder before using")
            return

        if not open_latest:
            used_capsule_name = self.ask_capsule_name()
            if not used_capsule_name:
                return
            used_capsule_real_name = meta_data_json[used_capsule_name]["capsule_name"]
            capsule_root_folder_dir = Path(meta_data_json[used_capsule_name]["assi_folder_dir"])

        def move_file(file_str, renamed_name):
            file = Path(file_str)
            print(f"Processing : {file}")

            if meta_data_json[used_capsule_name]["config"]["use_weekday"]:
                allowed_day_of_week = ["1", "2", "3", "4", "5"]
                if meta_data_json[used_capsule_name]["config"]["include_weekends"] == True:
                    allowed_day_of_week.append("6")
                    allowed_day_of_week.append("7")
                day_options = [
                    f"{d} : {DAY_OF_WEEK_REF_ENG[d]} ({DAY_OF_WEEK_REF[d]})"
                    for d in allowed_day_of_week
                ]
                chosen_day_str = ui_select("Day of week of the lesson:", day_options)
                if not chosen_day_str:
                    return
                day_of_week = chosen_day_str.split(" : ")[0]
                day_of_week = DAY_OF_WEEK_REF[day_of_week]
                searching_folder_dir = capsule_root_folder_dir / day_of_week
                if not searching_folder_dir.exists():
                    searching_folder_dir.mkdir(parents=True, exist_ok=True)
            else:
                searching_folder_dir = capsule_root_folder_dir

            dive_layer = meta_data_json[used_capsule_name]["config"]["dive_layer"]
            searching_layer = 1
            while searching_layer <= dive_layer:
                before_searching_folder_dir = searching_folder_dir
                searching_folder_dir = self.diving(searching_folder_dir)
                if before_searching_folder_dir == searching_folder_dir:
                    break
                searching_layer += 1

            target_folder_dir = searching_folder_dir
            print("-----")
            print(f"original path : {file}")
            if renamed_name != "":
                extension = file.suffix
                file_name = renamed_name + extension
            else:
                file_name = file.name
            destination = target_folder_dir / file_name

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
                    return
                reaction = int(reaction_str[0])

                if reaction == 0:
                    file_root_name = file.stem
                    extension = file.suffix
                    indexing = 1
                    while destination.exists():
                        file_name = f"{file_root_name}_{indexing}{extension}"
                        destination = target_folder_dir / file_name
                        indexing += 1
                elif reaction == 1:
                    print("Moving action interrupted")
                    return
                elif reaction == 2:
                    new_name = ui_input("Rename:")
                    if not new_name or new_name.strip() == "":
                        print("Moving action interrupted")
                        return
                    extension = file.suffix
                    file_name = new_name.strip() + extension
                    destination = target_folder_dir / file_name
                    if destination.exists():
                        print("This file name also exists")
                        print("Moving action interrupted")
                        return
                elif reaction == 3:
                    print("Please restart and select the versioning mode")
                    return
                elif reaction == 4:
                    pass
                else:
                    return

            if copy_and_move:
                shutil.copy2(file, destination)
            else:
                shutil.move(file, destination)
            print(f"Moved to {destination}")
            print("Successful")
            return str(destination)

        def version_file(file_str=None, renamed_name=None, is_recovering=False):
            version_dir = capsule_root_folder_dir / f"{used_capsule_real_name}_versioning"
            versioning_meta_data_json_path = version_dir / "versioning_meta_data.json"
            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
            else:
                print("No versioning collection exists")
                print("Please create a versioning collection")
                self.set_versioning_mode(capsule_name=used_capsule_name)
                return

            versioning_collections = list(versioning_meta_data_json.keys())
            selected = ui_select(
                "Select a versioning collection:",
                versioning_collections,
                extra_options=["No desired versioning collection"]
            )
            if not selected:
                return
            if selected == "No desired versioning collection":
                print("Redirect to set versioning mode")
                self.set_versioning_mode(capsule_name=used_capsule_name)
                return

            selected_versioning_collection = selected
            active_path = Path(versioning_meta_data_json[selected_versioning_collection]["active_path"])

            version_to_recover = None
            if is_recovering:
                version_keys = [
                    k for k in versioning_meta_data_json[selected_versioning_collection]
                    if k != "active_path"
                ]
                version_to_recover = ui_select("Select a version to recover:", [str(k) for k in version_keys])
                if not version_to_recover:
                    return
                if version_to_recover not in versioning_meta_data_json[selected_versioning_collection]:
                    print("The designated version does not exist")
                    return

            comment = ui_input("Input comments (leave blank for none):")
            comment = None if (comment is None or comment.strip() == "") else comment.strip()

            version_num = len(versioning_meta_data_json[selected_versioning_collection]) - 1
            archive_file_name = f"{active_path.stem}_ver{version_num}{active_path.suffix}"
            archived_path = version_dir / archive_file_name
            shutil.move(active_path, archived_path)

            if is_recovering:
                version_to_recover_meta_data = versioning_meta_data_json[selected_versioning_collection][version_to_recover]
                version_to_recover_path = Path(version_to_recover_meta_data["archived_path"])
                storing_path = active_path.parent / version_to_recover_path.name
                shutil.move(version_to_recover_path, storing_path)
            else:
                if renamed_name == "":
                    storing_path = active_path.parent / Path(file_str).name
                else:
                    extension = Path(file_str).suffix
                    storing_path = active_path.parent / f"{renamed_name}{extension}"
                shutil.move(Path(file_str), storing_path)

            versioning_meta_data_json[selected_versioning_collection]["active_path"] = str(storing_path)
            versioned_file_data = versioning_meta_data_json[selected_versioning_collection][str(version_num)]
            versioned_file_data["archived_path"] = str(archived_path)
            versioned_file_data["versioned_datetime"] = str(datetime.datetime.now())
            versioning_meta_data_json[selected_versioning_collection][str(version_num)] = versioned_file_data
            versioning_meta_data_json[selected_versioning_collection][str(version_num + 1)] = {
                "original_path": str(storing_path),
                "added_datetime": str(datetime.datetime.now()),
                "comments": comment
            }
            if recover_version:
                del versioning_meta_data_json[selected_versioning_collection][version_to_recover]

            with open(versioning_meta_data_json_path, "w", encoding="utf-8") as f:
                json.dump(versioning_meta_data_json, f, ensure_ascii=False, indent=3)
            print("File versioned successfully")
            return str(storing_path)

        def opening_file(is_open_previous=False):
            if not is_open_previous:
                dive_layer = meta_data_json[used_capsule_name]["config"]["dive_layer"]
                searching_folder_dir = meta_data_json[used_capsule_name]["assi_folder_dir"]
                if meta_data_json[used_capsule_name]["config"]["use_weekday"] == True:
                    dive_layer += 1
                while True:
                    before_searching_folder_dir = searching_folder_dir
                    searching_folder_dir = self.diving(searching_folder_dir, is_search_for_file=True)
                    if before_searching_folder_dir == searching_folder_dir:
                        break
                    if Path(searching_folder_dir).is_file():
                        break
                    if not ui_confirm("Proceed?"):
                        break
            else:
                if "latest_opened" in meta_data_json["app_config"]:
                    searching_folder_dir = Path(meta_data_json["app_config"]["latest_opened"])
                    if not searching_folder_dir.exists():
                        print("File not exist")
                        return
                else:
                    print("No latest opened file found")
                    return

            if platform.system() == "Darwin":
                subprocess.run(["open", "-R", searching_folder_dir])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", "/select", searching_folder_dir])
            else:
                print("Only MacOS and Windows are supported currently")
                return

        if is_open:
            opening_file()
        elif open_latest:
            opening_file(is_open_previous=True)
        elif recover_version:
            version_file(is_recovering=True)
        elif register_course:
            self.add_register_course()
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
                previous_file_path = move_file(your_assi_path, renamed_name)
            else:
                previous_file_path = version_file(file_str=your_assi_path, renamed_name=renamed_name)

            meta_data_json["app_config"]["latest_opened"] = previous_file_path
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)

    def register_course(self):
        while True:
            lesson_num_str = ui_input("Input number for lessons per day:")
            if lesson_num_str is None:
                return None
            if lesson_num_str.isdigit() and int(lesson_num_str) >= 2:
                lesson_num = int(lesson_num_str)
                break
            print("Please input a number larger than or equal to 2")

        registered_courses_info = {}
        print("Please input the course information for the lessons in the format of \"course name, course credit, course category\"")
        print("If there is no course for the lesson, just press enter")

        for day in range(1, 6):
            print("----------")
            print(DAY_OF_WEEK_REF_ENG[f"{day}"])
            day_course_info = {}
            for lesson in range(1, lesson_num + 1):
                course_registered = ui_input(f"Lesson {lesson} :")
                if course_registered is None:
                    course_registered = ""
                course_info = course_registered.split(",")
                course_name, course_credit, course_catagory = None, None, None
                try:
                    course_name = None if course_info[0].strip() == "" else course_info[0].strip()
                    course_credit = course_info[1].strip()
                    course_catagory = course_info[2].strip()
                except:
                    pass
                day_course_info[f"{lesson}"] = {
                    "course_name": course_name,
                    "course_credit": course_credit,
                    "course_catagory": course_catagory
                }
            registered_courses_info[f"{day}"] = day_course_info

        print("---------")
        print("Confirmation of registered courses : ")
        for day in registered_courses_info:
            print(DAY_OF_WEEK_REF_ENG[day])
            for lesson in registered_courses_info[day]:
                course_info = registered_courses_info[day][lesson]
                print(f"Lesson {lesson} : {course_info['course_name']}, {course_info['course_credit']}, {course_info['course_catagory']}")
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
        for day in registered_courses_info:
            day_folder_name = DAY_OF_WEEK_REF[day]
            day_folder_dir = Path(new_sem_dir) / sem_name / day_folder_name
            day_folder_dir.mkdir(parents=True, exist_ok=True)
            for lesson in registered_courses_info[day]:
                course_name = registered_courses_info[day][lesson]["course_name"]
                if course_name is not None:
                    course_folder_name = f"{lesson}限：{course_name}"
                    course_folder_dir = day_folder_dir / course_folder_name
                    course_folder_dir.mkdir(parents=True, exist_ok=True)
        print("Successfully registered courses and built assignment directory")
        return [str(Path(new_sem_dir) / sem_name), registered_courses_info]

    def initialization_mode(self, config_conversation=False, init_with_reg=False):
        if init_with_reg:
            course_info = self.register_course()
            if not course_info:
                return
            new_folder_dir = course_info[0]
            register_course_info = course_info[1]
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

        meta_data_raw = {
            "assi_folder_dir": new_folder_dir,
            "capsule_name": capsule_name,
            "config": CONFIG,
            "registered_courses": register_course_info if init_with_reg else None
        }

        if config_conversation:
            is_use_weekday = ui_confirm("Use the weekday based allocation system?")
            is_include_weekends = ui_confirm("Include weekends in your file system?")
            dive_layer_str = ui_input("Designate the number of dive layers:")
            dive_layer = int(dive_layer_str) if (dive_layer_str and dive_layer_str.isdigit()) else 1
            config_items_list = list(CONFIG.keys())
            meta_data_raw["config"] = {
                config_items_list[0]: is_use_weekday,
                config_items_list[1]: is_include_weekends,
                config_items_list[2]: dive_layer,
            }

        if len(self.meta_data_json) == 1:
            meta_data_json = self.meta_data_json
            meta_data_json["default"] = meta_data_raw
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False)
            print("New capsule created")
            print(f"capsule name : {capsule_name}")
            print(f"assignment folder directory : {new_folder_dir}")
        else:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                meta_data_current = json.load(f)
            while capsule_name in meta_data_current:
                print("Capsule name already exists")
                capsule_name = ui_input("Input your new capsule name:")
                if not capsule_name:
                    return
                capsule_name = capsule_name.strip()

            if ui_confirm("Make to default?"):
                current_default = meta_data_current["default"]
                new_name_for_current_default = current_default["capsule_name"]
                meta_data_current[new_name_for_current_default] = current_default
                meta_data_current["default"] = meta_data_raw
                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_current, f, ensure_ascii=False, indent=3)
                print("New capsule created and Set to default")
                print(f"capsule name : {capsule_name}")
                print(f"assignment folder directory : {new_folder_dir}")
            else:
                meta_data_current[capsule_name] = meta_data_raw
                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_current, f, ensure_ascii=False, indent=3)
                print("New capsule created")
                print(f"capsule name : {capsule_name}")
                print(f"assignment folder directory : {new_folder_dir}")

    def settings_mode(self):
        SETTING_ITEMS = {
            "1": "change default",
            "2": "change assignment folder",
            "3": "edit configurations",
            "4": "edit app configurations",
            "5": "update"
        }
        meta_data_json = self.meta_data_json
        setting_options = [f"{k} : {v}" for k, v in SETTING_ITEMS.items()]
        chosen = ui_select("Choose a setting item:", setting_options)
        if not chosen:
            return
        setting_item_selected = chosen.split(" : ")[0]

        if setting_item_selected in ["1", "2"]:
            if len(meta_data_json) == 1:
                print("There is no capsule to set")
                return

        if setting_item_selected == "1":
            if len(meta_data_json) == 2:
                print("There is only one capsule which is already in default")
                return
            print("Choose a capsule to set default")
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            if setting_capsule_name == "default":
                print("The selected capsule is already in default")
                return
            current_default_capsule_real_name = meta_data_json["default"]["capsule_name"]
            meta_data_json[current_default_capsule_real_name] = meta_data_json["default"]
            meta_data_json["default"] = meta_data_json[setting_capsule_name]
            del meta_data_json[setting_capsule_name]
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)
            print(f"Successfully set {setting_capsule_name} to default")

        elif setting_item_selected == "2":
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            is_confirmed = False
            while not is_confirmed:
                new_folder_dir = ui_input("Input the new directory for your assignment folder:")
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
            original_assi_folder_dir = meta_data_json[setting_capsule_name]["assi_folder_dir"]
            versioning_folder_name = f"{meta_data_json[setting_capsule_name]['capsule_name']}_versioning"
            origial_versioning_folder_path = Path(original_assi_folder_dir) / versioning_folder_name
            meta_data_json[setting_capsule_name]["assi_folder_dir"] = new_folder_dir
            if origial_versioning_folder_path.exists():
                shutil.move(origial_versioning_folder_path, Path(new_folder_dir))
            print(f"Successfully changed to : {new_folder_dir}")

        elif setting_item_selected == "3":
            meta_data_json = self.meta_data_json
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            config_items = list(CONFIG_CONVENTION.keys())

            is_continue_to_set = True
            while is_continue_to_set:
                print("Current Settings:")
                config_options = []
                for idx, config_item in enumerate(config_items):
                    orig = meta_data_json[setting_capsule_name]["config"][config_item]
                    label = f"{config_item} ({CONFIG_CONVENTION[config_item]}) - {orig}"
                    print(f"{idx+1} : {label}")
                    config_options.append(label)

                chosen_config = ui_select("Select item to edit:", config_options)
                if not chosen_config:
                    break
                item_to_set = config_items[config_options.index(chosen_config)]
                orig_val = meta_data_json[setting_capsule_name]["config"][item_to_set]

                if isinstance(orig_val, bool):
                    if ui_confirm(f"Switch {item_to_set} from {orig_val} to {not orig_val}?"):
                        meta_data_json[setting_capsule_name]["config"][item_to_set] = not orig_val
                elif isinstance(orig_val, int):
                    new_val_str = ui_input(f"Designate new value for {item_to_set}:", default=str(orig_val))
                    new_val = int(new_val_str) if (new_val_str and new_val_str.isdigit()) else orig_val
                    meta_data_json[setting_capsule_name]["config"][item_to_set] = new_val

                is_continue_to_set = ui_confirm("Edit other settings?")

            print("Current Settings:")
            for config_item in config_items:
                new_value = meta_data_json[setting_capsule_name]["config"][config_item]
                print(f"{config_item} ({CONFIG_CONVENTION[config_item]}) - {new_value}")
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)

        elif setting_item_selected == "4":
            if "app_config" in meta_data_json:
                bool_items = [k for k in meta_data_json["app_config"] if isinstance(meta_data_json["app_config"][k], bool)]
                if not bool_items:
                    print("No configurable app settings found")
                    return
                is_continue_to_set = True
                while is_continue_to_set:
                    print("Current app configurations : ")
                    app_options = [f"{k} - {meta_data_json['app_config'][k]}" for k in bool_items]
                    for opt in app_options:
                        print(f"  {opt}")
                    chosen_app = ui_select("Select item to toggle:", app_options)
                    if not chosen_app:
                        break
                    item_key = bool_items[app_options.index(chosen_app)]
                    meta_data_json["app_config"][item_key] = not meta_data_json["app_config"][item_key]
                    is_continue_to_set = ui_confirm("Edit other app configurations?")

                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_json, f, ensure_ascii=False, indent=3)
                print("Current app configurations : ")
                for k in bool_items:
                    print(f"{k} - {meta_data_json['app_config'][k]}")
            else:
                print("No app configuration found")
                meta_data_json["app_config"] = {}

        elif setting_item_selected == "5":
            try:
                from updater import update_from_git
            except:
                print("Unable to obtain the updater script")
                return
            update_from_git(self.current_dir, self.my_path)
            exit()

        else:
            print("Invalid")

    def help(self):
        info = ("""
                1 : continuing
                1n : renaming
                1v : versioning
                1o : opening
                1c : recovering
                1l : opening latest
                1p : copy and move
                1r : registering courses
                2 : creating new versioning collection
                2q : query versioning info
                2c : clear versioning data
                3 : creating new capsule
                3i : initialization with conversation
                3r : initialization with registrastion
                4 : settings
                """)
        print(info)


def main():
    ma = MyAssignment()

    mode_options = [
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
    chosen = ui_select("MyAssignment — Select a mode (or type directly e.g. 1v):", mode_options)
    if chosen is None:
        print("Cancelled.")
        return

    # 直接入力（例: "1v"）か、選択肢の文字列（例: "1v : continuation + versioning"）かを判定
    if " : " in chosen:
        mode = chosen.split(" : ")[0].strip()
    else:
        mode = chosen.strip()
    print("")

    regex_checker = re.fullmatch(r"\d[a-zA-Z]?", mode)
    if not regex_checker:
        print("Invalid mode")
    elif "1" in mode:
        ma.continuation_mode(
            is_renaming="n" in mode,
            versioning="v" in mode,
            is_open="o" in mode,
            recover_version="c" in mode,
            open_latest="l" in mode,
            copy_and_move="p" in mode,
            register_course="r" in mode
        )
    elif "2" in mode:
        ma.set_versioning_mode(
            is_query="q" in mode,
            is_clear="c" in mode
        )
    elif "3" in mode:
        ma.initialization_mode(
            config_conversation="i" in mode,
            init_with_reg="r" in mode
        )
    elif "4" in mode:
        ma.settings_mode()
    else:
        print("Invalid mode")
    print("")


if __name__ == "__main__":
    main()

# cd /Users/shiinaayame/Documents/Daily_tools/assignment_allocator ; python3 submitter.py
"""
TODOS:
1 in initialization, confirm no files are set to client folder *
2 avoid user from chooing app config which is not a capsule name  *
3 allow users to choose to copy and move *
4 allow users to terminate diving *
5 strengthen mode input check (now, for eg cat1 will also be treated as 1 and c in mode) *
6 the capsulename_versioning folder is not a normal folder so hide it in menu *
7 Space is accidentialy added the the collection dir name when setting
8 allow users to alter names of folders and files without crashing the app
9 Allow users to directly operate versioning collections after query

TODOS:
10 add options to app_config to improve usability
11 fix and update setting items 1 , 2 , 3 *
"""