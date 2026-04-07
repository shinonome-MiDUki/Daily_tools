from pathlib import Path
import json
import shutil
import os
import re
import sys
import datetime
import subprocess
import platform

from prompt_toolkit.shortcuts import (
    radiolist_dialog,
    input_dialog,
    message_dialog,
    yes_no_dialog,
)
from prompt_toolkit.styles import Style

DIALOG_STYLE = Style.from_dict({
    "dialog":             "bg:#1e1e2e",
    "dialog frame.label": "bg:#89b4fa fg:#1e1e2e",
    "dialog.body":        "bg:#313244 fg:#cdd6f4",
    "button":             "bg:#45475a fg:#cdd6f4",
    "button.focused":     "bg:#89b4fa fg:#1e1e2e",
    "radio-checked":      "fg:#a6e3a1",
    "radio":              "fg:#cdd6f4",
})

def ui_radio(title, text, values):
    """radiolist_dialog ラッパー。キャンセル時は None を返す。"""
    return radiolist_dialog(
        title=title,
        text=text,
        values=values,
        style=DIALOG_STYLE,
    ).run()

def ui_input(title, text, default="", password=False):
    """input_dialog ラッパー。キャンセル時は None を返す。"""
    return input_dialog(
        title=title,
        text=text,
        default=default,
        password=password,
        style=DIALOG_STYLE,
    ).run()

def ui_message(title, text):
    """message_dialog ラッパー。"""
    message_dialog(
        title=title,
        text=text,
        style=DIALOG_STYLE,
    ).run()

def ui_confirm(title, text):
    """yes_no_dialog ラッパー。True/False を返す。"""
    return yes_no_dialog(
        title=title,
        text=text,
        style=DIALOG_STYLE,
    ).run()

# ─────────────────────────────────────────────
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
            ui_message("Error", "No valid assignment folder is set\nPlease set a valid folder before using")
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
        values = [(name, name) for name in capsule_list]
        result = ui_radio("Capsule Selection", "Select a capsule:", values)
        return result if result else "default"

    def diving(self, searching_folder_dir_input, is_search_for_file=False):
        searching_folder_dir = Path(searching_folder_dir_input)
        if not is_search_for_file:
            target_names = [f.name for f in searching_folder_dir.iterdir() if f.is_dir()]
        else:
            target_names = [f.name for f in searching_folder_dir.iterdir()]

        ADD_NEW = "__ADD_NEW__"
        TERMINATE = "__TERMINATE__"
        values = [(name, name) for name in target_names]
        values.append((ADD_NEW, "Add new folder"))
        values.append((TERMINATE, "[t] Stay here / terminate diving"))

        target_selected = ui_radio(
            "Folder Selection",
            f"Current: {searching_folder_dir}\nSelect a folder:",
            values,
        )

        if target_selected is None or target_selected == TERMINATE:
            return searching_folder_dir

        if target_selected == ADD_NEW:
            target_name_to_add = ui_input("New Folder", "Input the folder name to add:")
            if not target_name_to_add:
                return searching_folder_dir
            # "_" shortcut: "folderName_subName"
            if "_" in target_name_to_add:
                parts = target_name_to_add.split("_", 1)
                # find parent folder by name
                matches = [n for n in target_names if n == parts[0]]
                if matches:
                    new_dir = searching_folder_dir / matches[0] / parts[1]
                else:
                    new_dir = searching_folder_dir / target_name_to_add
            else:
                new_dir = searching_folder_dir / target_name_to_add
            new_dir.mkdir(parents=True, exist_ok=True)
            return new_dir

        return searching_folder_dir / target_selected

    def show_course_today(self):
        today_day_of_week = str(datetime.datetime.today().isoweekday())
        defult_capsule_info = self.meta_data_json["default"]
        lines = []
        if "registered_courses" in defult_capsule_info and defult_capsule_info["registered_courses"] != None:
            registered_courses = defult_capsule_info["registered_courses"]
            if today_day_of_week in registered_courses:
                today_courses = registered_courses[today_day_of_week]
                lines.append("Today's courses:")
                for lesson in today_courses:
                    course_info = today_courses[lesson]
                    if course_info["course_name"] != None:
                        lines.append(f"Lesson {lesson} : {course_info['course_name']}")
            else:
                lines.append("No course registered for today")
        if lines:
            ui_message("Today's Schedule", "\n".join(lines))
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
                ui_message("Error", "No files found in the selected folder.")
                return
            values = [(name, name) for name in target_file_names]
            target_selected_name = ui_radio("File Selection", "Select a file:", values)
            if not target_selected_name:
                return
            target_selected_path = Path(searching_folder_dir) / target_selected_name

            comment = ui_input("Comments", "Input comments (leave blank for none):")
            comment = None if (comment is None or comment.strip() == "") else comment.strip()

            versioning_meta_data_json_path = versioning_dir / "versioning_meta_data.json"
            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
            else:
                versioning_meta_data_json = {}

            versioning_collection_alias = ui_input(
                "Collection Name",
                "Name this versioning collection:",
                default=f"{target_capsule_real_name}_{datetime.datetime.now()}"
            )
            if not versioning_collection_alias or versioning_collection_alias.strip() == "":
                versioning_collection_alias = f"{target_capsule_real_name}_{datetime.datetime.now()}"
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
            ui_message("Success", f"Successfully set up versioning collection:\n{versioning_collection_alias}")

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
                ui_message("Error", "No versioning collection exists")
                return

            versioning_collections = list(versioning_meta_data_json.keys())
            values = [(name, name) for name in versioning_collections]
            selected = ui_radio("Clear Collection", "Select a versioning collection:", values)
            if not selected:
                return
            selected_versioning_collection = selected

            confirmed = ui_confirm(
                "Confirm Clear",
                f"Clearing versioning collection:\n{selected_versioning_collection}\n\nAre you sure?"
            )
            if not confirmed:
                ui_message("Cancelled", "Clearing action cancelled")
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
            ui_message("Success", f"Successfully cleared versioning collection:\n{selected_versioning_collection}")

        def query_version():
            searching_words_raw = ui_input("Search Versioning", "Search (keyword_option1_option2 ...):")
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
                    ui_message("Result", "No versioning data found")
                    return

                result_lines = []
                is_have_something_matched_kw = False
                for versioning_collection in versioning_meta_data_json:
                    if keyword != "" and keyword.lower() not in str(versioning_collection).lower():
                        continue
                    is_have_something_matched_kw = True
                    result_lines.append(f"{versioning_collection} :")
                    collection_data = versioning_meta_data_json[versioning_collection]
                    for version in versioning_meta_data_json[versioning_collection]:
                        if version == "active_path":
                            result_lines.append(f"Active path : {collection_data['active_path']}")
                        else:
                            result_lines.append(f"Version {version} :")
                            version_data = collection_data[version]
                            for data_item in version_data:
                                if search_options:
                                    for search_option in search_options:
                                        if search_option.lower() in str(data_item).lower():
                                            result_lines.append(f"   {data_item} : {version_data[data_item]}")
                                            break
                                else:
                                    result_lines.append(f"   {data_item} : {version_data[data_item]}")
                    result_lines.append("-----")

                if not is_have_something_matched_kw:
                    ui_message("Result", "No matching versioning collection")
                else:
                    ui_message("Query Results", "\n".join(result_lines))
            else:
                ui_message("Error", "No versioning data found")

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
            ui_message("Info", "No registered courses found for this capsule\nRedirecting to course registration ...")
            self.register_course()
            return
        course_meta_data = meta_data_json[registering_capsule_name]["registered_courses"]

        while True:
            lesson_to_register = ui_input(
                "Register Lesson",
                "Input the lesson you want to register\n(e.g. 2-3 for Tuesday's 3rd lesson):"
            )
            if lesson_to_register is None:
                return
            lesson_to_register = lesson_to_register.strip()
            if re.match(r"\d+-\d+", lesson_to_register):
                break
            ui_message("Invalid", "Invalid input. Please use format: day-period (e.g. 2-3)")

        day_to_register = lesson_to_register.split("-")[0]
        period_to_register = lesson_to_register.split("-")[1]
        if day_to_register not in course_meta_data:
            ui_message("Error", "Invalid day of week")
            return
        if period_to_register not in course_meta_data[day_to_register]:
            ui_message("Error", "Invalid lesson period")
            return

        course_info = ui_input(
            "Course Information",
            'Input course info:\n"course name, course credit, course category"'
        )
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
            confirmed = ui_confirm(
                "Warning: Overwrite?",
                f"There is already a registered course:\n"
                f"{original_course_info['course_name']}, {original_course_info['course_credit']}, {original_course_info['course_catagory']}\n\n"
                "Do you want to overwrite?"
            )
            if not confirmed:
                ui_message("Cancelled", "Course registration cancelled")
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
        ui_message("Success", "Successfully registered course")

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
            ui_message("Error", "No default assignment folder is set\nPlease set default folder before using")
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
                day_values = [
                    (d, f"{DAY_OF_WEEK_REF_ENG[d]} ({DAY_OF_WEEK_REF[d]})")
                    for d in allowed_day_of_week
                ]
                day_of_week = ui_radio("Day of Week", "Day of week of the lesson:", day_values)
                if not day_of_week:
                    return
                day_of_week_label = DAY_OF_WEEK_REF[day_of_week]
                searching_folder_dir = capsule_root_folder_dir / day_of_week_label
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
                conflict_values = [
                    ("0", "Auto-resolve (default)"),
                    ("1", "Stop moving"),
                    ("2", "Rename it"),
                    ("3", "Do a versioning"),
                    ("4", "Overwrite the existing one"),
                ]
                reaction_str = ui_radio(
                    "File Conflict",
                    f"File already exists:\n{destination}\n\nHow do you want to handle it?",
                    conflict_values,
                )
                reaction = int(reaction_str) if reaction_str in [str(i) for i in range(0, 5)] else 0

                if reaction == 0:
                    file_root_name = file.stem
                    extension = file.suffix
                    indexing = 1
                    while destination.exists():
                        file_name = f"{file_root_name}_{indexing}{extension}"
                        destination = target_folder_dir / file_name
                        indexing += 1
                elif reaction == 1:
                    ui_message("Cancelled", "Moving action interrupted")
                    return
                elif reaction == 2:
                    new_name = ui_input("Rename", "Rename:")
                    if not new_name or new_name.strip() == "":
                        ui_message("Cancelled", "Moving action interrupted")
                        return
                    extension = file.suffix
                    file_name = new_name.strip() + extension
                    destination = target_folder_dir / file_name
                    if destination.exists():
                        ui_message("Error", "This file name also exists\nMoving action interrupted")
                        return
                elif reaction == 3:
                    ui_message("Info", "Please restart and select the versioning mode")
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
            ui_message("Success", f"Moved to:\n{destination}")
            return str(destination)

        def version_file(file_str=None, renamed_name=None, is_recovering=False):
            version_dir = capsule_root_folder_dir / f"{used_capsule_real_name}_versioning"
            versioning_meta_data_json_path = version_dir / "versioning_meta_data.json"
            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
            else:
                ui_message("Error", "No versioning collection exists\nPlease create a versioning collection")
                self.set_versioning_mode(capsule_name=used_capsule_name)
                return

            versioning_collections = list(versioning_meta_data_json.keys())
            NO_DESIRED = "__NO_DESIRED__"
            values = [(name, name) for name in versioning_collections]
            values.append((NO_DESIRED, "No desired versioning collection"))
            selected = ui_radio("Versioning Collection", "Select a versioning collection:", values)
            if not selected:
                return
            if selected == NO_DESIRED:
                ui_message("Info", "Redirect to set versioning mode")
                self.set_versioning_mode(capsule_name=used_capsule_name)
                return

            selected_versioning_collection = selected
            active_path = Path(versioning_meta_data_json[selected_versioning_collection]["active_path"])

            if is_recovering:
                version_keys = [
                    k for k in versioning_meta_data_json[selected_versioning_collection]
                    if k != "active_path"
                ]
                version_values = [(k, f"Version {k}") for k in version_keys]
                version_to_recover = ui_radio("Recover Version", "Select a version to recover:", version_values)
                if not version_to_recover:
                    return
                if version_to_recover not in versioning_meta_data_json[selected_versioning_collection]:
                    ui_message("Error", "The designated version does not exist")
                    return

            comment = ui_input("Comments", "Input comments (leave blank for none):")
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
            ui_message("Success", "File versioned successfully")
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
                    proceed = ui_confirm("Proceed?", f"Current path:\n{searching_folder_dir}\n\nProceed diving?")
                    if not proceed:
                        break
            else:
                if "latest_opened" in meta_data_json["app_config"]:
                    searching_folder_dir = Path(meta_data_json["app_config"]["latest_opened"])
                    if not searching_folder_dir.exists():
                        ui_message("Error", "File not exist")
                        return
                else:
                    ui_message("Error", "No latest opened file found")
                    return

            if platform.system() == "Darwin":
                subprocess.run(["open", "-R", searching_folder_dir])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", "/select", searching_folder_dir])
            else:
                ui_message("Error", "Only MacOS and Windows are supported currently")
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
            your_assi_path = ui_input("Assignment File", "Drag your assignment here (paste the path):")
            if not your_assi_path:
                return
            your_assi_path = your_assi_path.strip()
            renamed_name = ""
            if is_renaming:
                renamed_name = ui_input("Rename", "Rename as:")
                if renamed_name is None:
                    renamed_name = ""
                renamed_name = renamed_name.strip()

            if not versioning:
                previous_file_path = move_file(your_assi_path, renamed_name)
            else:
                previous_file_path = version_file(file_str=your_assi_path, renamed_name=renamed_name)

            meta_data_json["app_config"]["latest_opened"] = previous_file_path
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)

    def register_course(self):
        while True:
            lesson_num_str = ui_input("Lessons per Day", "Input number for lessons per day:")
            if lesson_num_str is None:
                return None
            if lesson_num_str.isdigit() and int(lesson_num_str) >= 2:
                lesson_num = int(lesson_num_str)
                break
            ui_message("Invalid", "Please input a number larger than or equal to 2")

        registered_courses_info = {}
        print("Please input the course information for the lessons in the format of \"course name, course credit, course category\"")
        print("If there is no course for the lesson, just press enter")

        for day in range(1, 6):
            day_course_info = {}
            for lesson in range(1, lesson_num + 1):
                course_registered = ui_input(
                    f"{DAY_OF_WEEK_REF_ENG[str(day)]} - Lesson {lesson}",
                    f'Input course info for {DAY_OF_WEEK_REF_ENG[str(day)]} Lesson {lesson}:\n"course name, course credit, course category"\n(leave blank if no course)'
                )
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

        confirm_lines = ["Confirmation of registered courses:"]
        for day in registered_courses_info:
            confirm_lines.append(DAY_OF_WEEK_REF_ENG[day])
            for lesson in registered_courses_info[day]:
                ci = registered_courses_info[day][lesson]
                confirm_lines.append(f"Lesson {lesson} : {ci['course_name']}, {ci['course_credit']}, {ci['course_catagory']}")
        confirmed = ui_confirm("Confirm Courses", "\n".join(confirm_lines) + "\n\nConfirm registered courses?")
        if not confirmed:
            ui_message("Cancelled", "Course registration cancelled")
            return None

        while True:
            sem_name = ui_input("Semester Name", "Input semester name:")
            if sem_name and sem_name.strip():
                sem_name = sem_name.strip()
                break
            ui_message("Invalid", "Please input a valid semester name")

        is_confirmed = False
        while not is_confirmed:
            new_sem_dir = ui_input("Semester Directory", "Input a directory for the semester:")
            if not new_sem_dir:
                return None
            new_sem_dir = new_sem_dir.strip()
            if Path(new_sem_dir).is_dir():
                is_confirmed = ui_confirm("Confirm Directory", f"Confirm the directory for your new semester:\n{new_sem_dir}")
            else:
                use_parent = ui_confirm(
                    "Not a Directory",
                    "The designated path is a file, not a directory.\nUse the parent directory instead?"
                )
                if use_parent:
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

        ui_message("Success", "Successfully registered courses and built assignment directory")
        return [str(Path(new_sem_dir) / sem_name), registered_courses_info]

    def initialization_mode(self, config_conversation=False, init_with_reg=False):
        if init_with_reg:
            course_info = self.register_course()
            if not course_info:
                return
            new_folder_dir = course_info[0]
            register_course_info = course_info[1]
        else:
            ui_message("Info", "Create new assignment capsule here")
            is_confirmed = False
            while not is_confirmed:
                new_folder_dir = ui_input("Assignment Folder", "Input a directory for your new assignment folder:")
                if not new_folder_dir:
                    return
                new_folder_dir = new_folder_dir.strip()
                if Path(new_folder_dir).is_dir():
                    is_confirmed = ui_confirm("Confirm Directory", f"Confirm the directory of your new assignment folder:\n{new_folder_dir}")
                else:
                    use_parent = ui_confirm(
                        "Not a Directory",
                        "The designated path is a file, not a directory.\nUse the parent directory instead?"
                    )
                    if use_parent:
                        is_confirmed = True
                        new_folder_dir = str(Path(new_folder_dir).resolve().parent)
            if not Path(new_folder_dir).exists:
                os.makedirs(new_folder_dir, exist_ok=True)
            register_course_info = None

        capsule_name = ui_input("Capsule Name", "Input your new capsule name:")
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
            is_use_weekday = ui_confirm("Config", "Use the weekday based allocation system?")
            is_include_weekends = ui_confirm("Config", "Include weekends in your file system?")
            dive_layer_str = ui_input("Config", "Designate the number of dive layers:")
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
            ui_message("Success", f"New capsule created\nCapsule name : {capsule_name}\nFolder : {new_folder_dir}")
        else:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                meta_data_current = json.load(f)
            while capsule_name in meta_data_current:
                ui_message("Error", "Capsule name already exists")
                capsule_name = ui_input("Capsule Name", "Input your new capsule name:")
                if not capsule_name:
                    return
                capsule_name = capsule_name.strip()

            make_to_default = ui_confirm("Set Default?", "Make this capsule the default?")
            if make_to_default:
                current_default = meta_data_current["default"]
                new_name_for_current_default = current_default["capsule_name"]
                meta_data_current[new_name_for_current_default] = current_default
                meta_data_current["default"] = meta_data_raw
                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_current, f, ensure_ascii=False, indent=3)
                ui_message("Success", f"New capsule created and set to default\nCapsule name : {capsule_name}\nFolder : {new_folder_dir}")
            else:
                meta_data_current[capsule_name] = meta_data_raw
                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_current, f, ensure_ascii=False, indent=3)
                ui_message("Success", f"New capsule created\nCapsule name : {capsule_name}\nFolder : {new_folder_dir}")

    def settings_mode(self):
        SETTING_ITEMS = {
            "1": "change default",
            "2": "change assignment folder",
            "3": "edit configurations",
            "4": "edit app configurations",
            "5": "update"
        }
        meta_data_json = self.meta_data_json
        setting_values = [(k, v) for k, v in SETTING_ITEMS.items()]
        setting_item_selected = ui_radio("Settings", "Choose a setting item:", setting_values)
        if not setting_item_selected:
            return

        if setting_item_selected in ["1", "2"]:
            if len(meta_data_json) == 1:
                ui_message("Error", "There is no capsule to set")
                return

        if setting_item_selected == "1":
            if len(meta_data_json) == 2:
                ui_message("Info", "There is only one capsule which is already in default")
                return
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            if setting_capsule_name == "default":
                ui_message("Info", "The selected capsule is already in default")
                return
            current_default_capsule_real_name = meta_data_json["default"]["capsule_name"]
            meta_data_json[current_default_capsule_real_name] = meta_data_json["default"]
            meta_data_json["default"] = meta_data_json[setting_capsule_name]
            del meta_data_json[setting_capsule_name]
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)
            ui_message("Success", f"Successfully set {setting_capsule_name} to default")

        elif setting_item_selected == "2":
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            is_confirmed = False
            while not is_confirmed:
                new_folder_dir = ui_input("New Folder", "Input the new directory for your assignment folder:")
                if not new_folder_dir:
                    return
                new_folder_dir = new_folder_dir.strip()
                if Path(new_folder_dir).is_dir():
                    is_confirmed = ui_confirm("Confirm Directory", f"Confirm the new directory:\n{new_folder_dir}")
                else:
                    use_parent = ui_confirm(
                        "Not a Directory",
                        "The designated path is a file, not a directory.\nUse the parent directory instead?"
                    )
                    if use_parent:
                        is_confirmed = True
                        new_folder_dir = str(Path(new_folder_dir).resolve().parent)
            original_assi_folder_dir = meta_data_json[setting_capsule_name]["assi_folder_dir"]
            versioning_folder_name = f"{meta_data_json[setting_capsule_name]['capsule_name']}_versioning"
            origial_versioning_folder_path = Path(original_assi_folder_dir) / versioning_folder_name
            meta_data_json[setting_capsule_name]["assi_folder_dir"] = new_folder_dir
            if origial_versioning_folder_path.exists():
                shutil.move(origial_versioning_folder_path, Path(new_folder_dir))
            ui_message("Success", f"Successfully changed to:\n{new_folder_dir}")

        elif setting_item_selected == "3":
            meta_data_json = self.meta_data_json
            setting_capsule_name = self.ask_capsule_name()
            if not setting_capsule_name:
                return
            config_items = list(CONFIG_CONVENTION.keys())

            is_continue_to_set = True
            while is_continue_to_set:
                current_settings_lines = ["Current Settings:"]
                config_values = []
                for idx, config_item in enumerate(config_items):
                    orig = meta_data_json[setting_capsule_name]["config"][config_item]
                    label = f"{config_item} ({CONFIG_CONVENTION[config_item]}) - {orig}"
                    current_settings_lines.append(f"{idx+1} : {label}")
                    config_values.append((config_item, label))

                item_to_set = ui_radio("Edit Configuration", "\n".join(current_settings_lines) + "\n\nSelect item to edit:", config_values)
                if not item_to_set:
                    break
                orig_val = meta_data_json[setting_capsule_name]["config"][item_to_set]
                if isinstance(orig_val, bool):
                    do_switch = ui_confirm("Switch Value", f"Switch {item_to_set}\nfrom {orig_val} → {not orig_val}?")
                    if do_switch:
                        meta_data_json[setting_capsule_name]["config"][item_to_set] = not orig_val
                elif isinstance(orig_val, int):
                    new_val_str = ui_input("Set Value", f"Designate new value for {item_to_set}:", default=str(orig_val))
                    new_val = int(new_val_str) if (new_val_str and new_val_str.isdigit()) else orig_val
                    meta_data_json[setting_capsule_name]["config"][item_to_set] = new_val

                is_continue_to_set = ui_confirm("Continue?", "Edit other settings?")

            result_lines = ["Updated Settings:"]
            for config_item in config_items:
                new_value = meta_data_json[setting_capsule_name]["config"][config_item]
                result_lines.append(f"{config_item} ({CONFIG_CONVENTION[config_item]}) - {new_value}")
            ui_message("Settings Saved", "\n".join(result_lines))
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)

        elif setting_item_selected == "4":
            if "app_config" in meta_data_json:
                bool_items = [k for k in meta_data_json["app_config"] if isinstance(meta_data_json["app_config"][k], bool)]
                if not bool_items:
                    ui_message("Info", "No configurable app settings found")
                    return
                is_continue_to_set = True
                while is_continue_to_set:
                    current_lines = ["Current app configurations:"]
                    values = []
                    for item in bool_items:
                        label = f"{item} - {meta_data_json['app_config'][item]}"
                        current_lines.append(label)
                        values.append((item, label))
                    item_to_set = ui_radio("App Config", "\n".join(current_lines) + "\n\nSelect item to toggle:", values)
                    if not item_to_set:
                        break
                    meta_data_json["app_config"][item_to_set] = not meta_data_json["app_config"][item_to_set]
                    is_continue_to_set = ui_confirm("Continue?", "Edit other app configurations?")

                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_json, f, ensure_ascii=False, indent=3)
                result_lines = ["Current app configurations:"]
                for k in bool_items:
                    result_lines.append(f"{k} - {meta_data_json['app_config'][k]}")
                ui_message("App Config Saved", "\n".join(result_lines))
            else:
                ui_message("Error", "No app configuration found")
                meta_data_json["app_config"] = {}

        elif setting_item_selected == "5":
            try:
                from updater import update_from_git
            except:
                ui_message("Error", "Unable to obtain the updater script")
                return
            update_from_git(self.current_dir, self.my_path)
            exit()

    def help(self):
        info = (
            "1  : continuing\n"
            "1n : renaming\n"
            "1v : versioning\n"
            "1o : opening\n"
            "1c : recovering\n"
            "1l : opening latest\n"
            "1p : copy and move\n"
            "1r : registering courses\n"
            "2  : creating new versioning collection\n"
            "2q : query versioning info\n"
            "2c : clear versioning data\n"
            "3  : creating new capsule\n"
            "3i : initialization with conversation\n"
            "3r : initialization with registration\n"
            "4  : settings"
        )
        ui_message("Help - Mode List", info)


def main():
    ma = MyAssignment()

    mode_values = [
        ("1",  "1  : continuation"),
        ("1n", "1n : continuation + rename"),
        ("1v", "1v : continuation + versioning"),
        ("1o", "1o : open file"),
        ("1c", "1c : recover version"),
        ("1l", "1l : open latest"),
        ("1p", "1p : copy and move"),
        ("1r", "1r : register course"),
        ("2",  "2  : new versioning collection"),
        ("2q", "2q : query versioning"),
        ("2c", "2c : clear versioning"),
        ("3",  "3  : new capsule"),
        ("3i", "3i : init with conversation"),
        ("3r", "3r : init with registration"),
        ("4",  "4  : settings"),
        ("5",  "5  : help"),
    ]
    mode = ui_radio("MyAssignment", "Select a mode:", mode_values)
    if mode is None:
        print("Cancelled.")
        return
    print("")

    regex_checker = re.fullmatch(r"\d[a-z|A-Z]?", mode)
    if not regex_checker:
        ui_message("Error", "Invalid mode")
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
    elif "5" in mode:
        ma.help()
        main()
    else:
        ui_message("Error", "Invalid mode")
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
