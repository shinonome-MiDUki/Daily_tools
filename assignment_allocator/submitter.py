from pathlib import Path
import json
import shutil
import os
import re
import sys
import datetime
import subprocess
import platform

print("Welcome to MyAssignment")
print(" ")

DAY_OF_WEEK_REF = {
    "1" : "月",
    "2" : "火",
    "3" : "水",
    "4" : "木",
    "5" : "金",
    "6" : "土",
    "7" : "日"
}
DAY_OF_WEEK_REF_ENG = {
    "1" : "Mon",
    "2" : "Tue",        
    "3" : "Wed",
    "4" : "Thu",
    "5" : "Fri",
    "6" : "Sat",
    "7" : "Sun"
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
            used_capsule_name = "default"
        else:
            k = 1
            capsule_list = []
            for capsule_name in self.meta_data_json:
                if capsule_name == "app_config":
                    continue
                print(f"{k} : {capsule_name}")
                capsule_list.append(capsule_name)
                k += 1
            used_capsule = str(input("Select a capsule: "))
            while used_capsule not in [f"{j}" for j in range(1,k)]:
                if used_capsule == "": 
                    used_capsule_name = "default"
                    return used_capsule_name
                print("Invalid")
                used_capsule = str(input("Select a capsule: "))
            used_capsule_name = capsule_list[int(used_capsule)-1] if used_capsule in [f"{j}" for j in range(1,k)] else "default"
        return used_capsule_name
    
    def diving(self, searching_folder_dir_input, is_search_for_file=False):
        searching_folder_dir = Path(searching_folder_dir_input)
        if not is_search_for_file:
            target_names = [f.name for f in searching_folder_dir.iterdir() if f.is_dir()]
        else:
            target_names = [f.name for f in searching_folder_dir.iterdir()]
        i = 1
        for target_name in target_names:
            print(f"{i} : {target_name}")
            i += 1
        print(f"{i} : Add new folder")
        target_selected = str(input("Select a folder : "))
        while (target_selected not in [f"{j}" for j in range(1,i+1)] 
               and "_" not in target_selected 
               and "t" not in target_selected):
            print("Invalid")
            target_selected = str(input("Select a folder : "))
        
        if "t" in target_selected:
            return searching_folder_dir

        if target_selected == f"{i}":
            target_name_to_add = str(input("Input the folder name to add : "))
            target_dir_to_make = searching_folder_dir / target_name_to_add
            target_dir_to_make.mkdir(parents=True, exist_ok=True)
            target_names.append(target_name_to_add)
        
        if "_" in target_selected:
            try:
                target_selected_break = target_selected.split("_")
                target_selected = target_selected_break[0]
                searching_folder_dir = searching_folder_dir / target_names[int(target_selected)-1]
                searching_folder_dir = searching_folder_dir / target_selected_break[-1]
                if not searching_folder_dir.exists():
                    searching_folder_dir.mkdir(parents=True, exist_ok=True)
            except:
                print("Invalid Input")
                return
        else:
            searching_folder_dir = searching_folder_dir / target_names[int(target_selected)-1]

        return searching_folder_dir
    
    def show_course_today(self):
        #use default capsule for showing today's course
        meta_data_json = self.meta_data_json
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
            target_capsule_name = self.ask_capsule_name() if capsule_name == None else capsule_name
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
            target_file_names = [f.name for f in searching_folder_dir.iterdir()]
            i = 1
            for target_file_name in target_file_names:
                print(f"{i} : {target_file_name}")
                i += 1
            target_selected = str(input("Select a file : "))
            while target_selected not in [f"{j}" for j in range(1,i)]:
                print("Invalid")
                target_selected = str(input("Select a file : "))
            target_selected_name = target_file_names[int(target_selected)-1]
            target_selected_path = searching_folder_dir / target_selected_name

            comment = str(input("Input comments")).strip()
            comment = None if comment == "" else comment

            versioning_meta_data_json_path = versioning_dir / "versioning_meta_data.json"
            if versioning_meta_data_json_path.exists():
                with open(versioning_meta_data_json_path, "r", encoding="utf-8") as f:
                    versioning_meta_data_json = json.load(f)
            else:
                versioning_meta_data_json = {}
            versioning_collection_alias = str(input("Name this versioning collection : ")).strip()
            if versioning_collection_alias == "":
                versioning_collection_alias = f"{target_capsule_real_name}_{datetime.datetime.now()}"
            versioning_meta_data_json[versioning_collection_alias] = {
                "active_path" : str(target_selected_path),
                1 : {
                    "original_path" : str(target_selected_path),
                    "added_datetime" : str(datetime.datetime.now()),
                    "versioned_datetime" : str(datetime.datetime.now()),
                    "comments" : comment
                }
            }
            with open(versioning_meta_data_json_path, "w", encoding="utf-8") as f:
                json.dump(versioning_meta_data_json, f, ensure_ascii=False, indent=3)
            print(f"Successfully set up versioning collection : {versioning_collection_alias}")
            
        def clear_collection():
            target_capsule_name = self.ask_capsule_name()
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
            
            i = 1
            versioning_collections = []
            for versioning_collection in versioning_meta_data_json:
                print(f"{i} : {versioning_collection}")
                versioning_collections.append(versioning_collection)
                i += 1
            target_selected = str(input("Select a versioning collection : "))
            while target_selected not in [f"{j}" for j in range(1,i)]:
                print("Invalid")
                target_selected = str(input("Select a versioning collection : "))
            selected_versioning_collection = versioning_collections[int(target_selected)-1]
            confirmation = str(input(f"Clearing versioning collection {selected_versioning_collection}. Confirm? (y/N) "))
            if confirmation not in ["y", "Y"]:
                print("Clearinf action cancelled")
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
            searching_words = str(input("Search : ")).strip().split("_")
            keyword = searching_words[0]
            search_options = searching_words[1:] if len(searching_words) > 1 else []
            meta_data_json = self.meta_data_json
            target_capsule_name = self.ask_capsule_name() if capsule_name == None else capsule_name
            capsule_root_folder_dir = meta_data_json[target_capsule_name]["assi_folder_dir"]
            target_capsule_real_name =  meta_data_json[target_capsule_name]["capsule_name"]
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
                            print(f"Active path : {collection_data["active_path"]}")
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
                return

        if is_query:
            query_version()
        elif is_clear:
            clear_collection()
        else:
            set_version(capsule_name)

    def add_register_course(self):
        registering_capsule_name = self.ask_capsule_name()
        meta_data_json = self.meta_data_json
        if "registered_courses" not in meta_data_json[registering_capsule_name] or meta_data_json[registering_capsule_name]["registered_courses"] == None:
            print("No registered courses found for this capsule")
            print("Redirecting to course registration ...")
            self.register_course()
            return
        course_meta_data = meta_data_json[registering_capsule_name]["registered_courses"]
        lesson_to_register = str(input("Input the lesson you want to register (e.g. 2-3 for Tuesday's 3rd lesson) : ")).strip()
        while not re.match(r"\d+-\d+", lesson_to_register):
            print("Invalid input")
            lesson_to_register = str(input("Input the lesson you want to register (e.g. 2-3 for Tuesday's 3rd lesson) : ")).strip()
        day_to_register = lesson_to_register.split("-")[0]
        period_to_register = lesson_to_register.split("-")[1]
        if day_to_register not in course_meta_data:
            print("Invalid day of week")
            return
        if period_to_register not in course_meta_data[day_to_register]:
            print("Invalid lesson period")
            return
        course_info = str(input("Input course information in the format of \"course name, course credit, course catagory\" \n→ "))
        course_info_split = course_info.split(",")
        course_name, course_credit, course_catagory = None, None, None
        try:
            course_name = None if course_info_split[0].strip(" ") == "" else course_info_split[0].strip(" ")
            course_credit = course_info_split[1].strip(" ")
            course_catagory = course_info_split[2].strip(" ")
        except:
            pass
        original_course_info = course_meta_data[day_to_register][period_to_register]
        if original_course_info["course_name"] != None:
            print("Warning : There is already a registered course for the designated lesson : "
                  f"\n{original_course_info['course_name']}, {original_course_info['course_credit']}, {original_course_info['course_catagory']}")
            confirmation = str(input("Do you want to overwrite the existing course information? (y/N) "))
            if confirmation not in ["y", "Y"]:
                print("Course registration cancelled")
                return
            os.rename(
                Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"{period_to_register}限：{original_course_info['course_name']}",
                Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"Original_{period_to_register}限：{original_course_info['course_name']}"
            )
            os.makedirs(Path(meta_data_json[registering_capsule_name]["assi_folder_dir"]) / DAY_OF_WEEK_REF[day_to_register] / f"{period_to_register}限：{course_name}", exist_ok=True)
        elif course_name == None:
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
                day_of_week = str(input(f"Day of week of the lesson (1-{allowed_day_of_week[-1]}): "))
                while day_of_week not in allowed_day_of_week:
                    print("Invalid")
                    day_of_week = str(input(f"Day of week of the lesson (1-{allowed_day_of_week[-1]}): "))
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
                file_name =file.name
            destination = target_folder_dir / file_name

            if destination.exists():
                print(destination)
                print("This file name already exists. You can choose to overwrite the existing one, do a versioning, or stop moving")
                reaction = str(input("You can input :\n0 to auto-resolve (default)\n1 to stop moving\n2 to rename it\n3 to do a versioning\n4 to overwrite the existing one\ninput→")).strip()
                reaction = int(reaction) if reaction in [str(i) for i in range(0,5)] else 0
                if reaction == 0:
                    file_root_name = file.stem
                    extension = file.suffix
                    indexing = 1
                    while destination.exists():
                        file_name = f"{file_root_name}_{indexing}{extension}"
                        destination = target_folder_dir / file_name
                        indexing += 1
                elif reaction == 1: 
                    print("Moving action interupted")
                    return
                elif reaction == 2:
                    new_name = str(input("Rename: ")).strip()
                    if new_name == "": 
                        print("Moving action interupted")
                        return
                    extension = file.suffix
                    file_name = new_name + extension
                    destination = target_folder_dir / file_name
                    if destination.exists():
                        print("This file name also exists")
                        print("Moving action interupted")
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
            
            i = 1
            versioning_collections = []
            for versioning_collection in versioning_meta_data_json:
                print(f"{i} : {versioning_collection}")
                versioning_collections.append(versioning_collection)
                i += 1
            print(f"{i} : No desired versioning collection")
            target_selected = str(input("Select a versioning collection : "))
            while target_selected not in [f"{j}" for j in range(1,i+1)]:
                print("Invalid")
                target_selected = str(input("Select a versioning collection : "))
            if target_selected == str(i):
                print("Redirect to set versioning mode")
                self.set_versioning_mode(capsule_name=used_capsule_name)
                return
            
            selected_versioning_collection = versioning_collections[int(target_selected)-1]
            active_path = Path(versioning_meta_data_json[selected_versioning_collection]["active_path"])
            
            if is_recovering:
                version_to_recover = str(input("Select a version to recover : "))
                if version_to_recover not in versioning_meta_data_json[selected_versioning_collection]:
                    print("The designated version does not exist")
                    return

            comment = str(input("Input comments")).strip()
            comment = None if comment == "" else comment
            
            version_num = len(versioning_meta_data_json[selected_versioning_collection])-1
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
            versioning_meta_data_json[selected_versioning_collection][str(version_num+1)] = {
                "original_path" : str(storing_path),
                "added_datetime" : str(datetime.datetime.now()),
                "comments" : comment
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
                searching_layer = 1
                if meta_data_json[used_capsule_name]["config"]["use_weekday"] == True:
                    dive_layer += 1
                while True:
                    before_searching_folder_dir = searching_folder_dir
                    searching_folder_dir = self.diving(searching_folder_dir, is_search_for_file=True)
                    if before_searching_folder_dir == searching_folder_dir:
                        break
                    if searching_folder_dir.is_file(): break
                    proceed_confirmation = str(input("Proceed? (Y/n)"))
                    if proceed_confirmation in ["n", "N"]: break
            else:
                if "latest_opened" in meta_data_json["app_config"]:
                    searching_folder_dir = Path(meta_data_json["app_config"]["latest_opened"])
                    if not searching_folder_dir.exists():
                        print("File not exist")
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
            your_assi_path = str(input("Drag your assignment here : ")).strip()
            renamed_name = str(input("Rename as : ")).strip() if is_renaming else ""
            if not versioning:
                previous_file_path = move_file(your_assi_path, renamed_name)
            else:
                previous_file_path = version_file(file_str=your_assi_path, renamed_name=renamed_name)

            meta_data_json["app_config"]["latest_opened"] = previous_file_path
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)

    def register_course(self):
        lesson_num = input("Input number for lessons per day : ")
        while not lesson_num.isdigit():
            print("Please input a number")
            lesson_num = input("Input number for lessons per day : ")
        lesson_num = int(lesson_num)
        while lesson_num < 2:
            print("Please input a number larger than 2")
            lesson_num = input("Input number for lessons per day : ")
            lesson_num = int(lesson_num)
        registered_courses_info = {}
        print("Please input the course information for the lessons in the format of \"course name, course credit, course catagory\"")
        print("If there is no course for the lesson, just press enter")
        for day in range(1,6):
            print("----------")
            print(DAY_OF_WEEK_REF_ENG[f"{day}"])
            day_course_info = {}
            for lesson in range(1, lesson_num+1):
                course_registered = str(input(f"Lesson {lesson} : "))
                course_info = course_registered.split(",")
                course_name, course_credit, course_catagory = None, None, None
                try:
                    course_name = None if course_info[0].strip(" ") == "" else course_info[0].strip(" ")
                    course_credit = course_info[1].strip(" ")
                    course_catagory = course_info[2].strip(" ")
                except:
                    pass
                day_course_info[f"{lesson}"] = {
                    "course_name" : course_name,
                    "course_credit" : course_credit,
                    "course_catagory" : course_catagory
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
        confirmation = str(input("Confirm registered courses? (y/N) : "))
        if confirmation not in ["y", "Y"]:
            print("Course registration cancelled")
            return None
        sem_name = str(input("Input semester name : "))
        while sem_name == "":
            print("Please input a valid semester name")
            sem_name = str(input("Input semester name : "))
        is_confirmed = False
        while not is_confirmed:
            new_sem_dir = str(input("Input a directory for the semester : ")).strip()
            if Path(new_sem_dir).is_dir():
                print(f"Confirmarion : {new_sem_dir}")
                confirmation = str(input("Please confirm the directory for your new semester (Y/n) : "))
                is_confirmed = False if confirmation in ["n", "N"] else True
            else:
                print("The designated is a file path instread of a directory. File paths cannot be used as directories")
                confirmation = str(input("Please confirm if you want to set the parent directory of your designated file path for your new semester (y/N) : "))
                if confirmation in ["y", "Y"]:
                    is_confirmed = True
                    new_sem_dir = str(Path(new_sem_dir).resolve().parent)
                else:
                    is_confirmed = False
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
                if course_name != None:
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
                new_folder_dir = str(input("Input a directory for your new assignment folder : ")).strip()
                if Path(new_folder_dir).is_dir():
                    print(f"Confirmarion : {new_folder_dir}")
                    confirmation = str(input("Please confirm the directory of your new assignment folder (Y/n) : "))
                    is_confirmed = False if confirmation in ["n", "N"] else True
                else:
                    print("The designated is a file path instread of a directory. File paths cannot be used as directories")
                    confirmation = str(input("Please confirm if you want to set the parent directory of your designated file path as your assignment directory (y/N) : "))
                    if confirmation in ["y", "Y"]:
                        is_confirmed = True
                        new_folder_dir = str(Path(new_folder_dir).resolve().parent)
                    else:
                        is_confirmed = False
            if not Path(new_folder_dir).exists:
                os.makedirs(new_folder_dir, exist_ok=True)
            
        capsule_name = str(input("Input your new capsule name : "))

        meta_data_raw = {
            "assi_folder_dir" : new_folder_dir,
            "capsule_name" : capsule_name,
            "config": CONFIG,
            "registered_courses" : register_course_info if init_with_reg else None
        }

        if config_conversation:
            is_use_weekday = True if str(input("Use the weekday based allocation system? (Y/n) ")) not in ["n", "N"] else False
            is_include_weekends = False if str(input("Include weekends in your file system? (y/N) ")) not in ["y", "Y"] else True
            dive_layer = input("Designate the number of dive layer : ")
            dive_layer = int(dive_layer) if str(dive_layer).isdigit() == True else 1
            config_items_list = [config_item for config_item in CONFIG]
            config_dic = {
                config_items_list[0]: is_use_weekday,
                config_items_list[1]: is_include_weekends,
                config_items_list[2]: dive_layer
            } #"use_weekday", "include_weekends", "dive_layer"
            meta_data_raw["config"] = config_dic

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
                capsule_name = str(input("Input your new capsule name : "))

            make_to_default = str(input("Make to default? (Y/N) : "))
            if make_to_default == "Y":
                current_default = meta_data_current["default"]
                new_name_for_current_default = current_default["capsule_name"]
                meta_data_current[new_name_for_current_default] = current_default
                meta_data_current["default"] = meta_data_raw
                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_current, f, ensure_ascii=False, indent=3)
                print("New capsule craeted and Set to default")
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
            "1" : "change default",
            "2" : "change assignment folder", 
            "3" : "edit configurations",
            "4" : "edit app configurations",
            "5" : "update"
        }
        meta_data_json = self.meta_data_json
        for setting_item in SETTING_ITEMS:
            print(f"{setting_item} : {SETTING_ITEMS[setting_item]}")
        setting_item_selected = str(input("Choose a setting item : "))
        while setting_item_selected not in [f"{j}" for j in range(1,len(SETTING_ITEMS)+1)]:
            print("Invalid")
            setting_item_selected = str(input("Choose a setting item : "))

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
            new_folder_dir = str(input("Input the new directory for your assignment folder : ")).strip()
            is_confirmed = False
            while not is_confirmed:
                new_folder_dir = str(input("Input the new directory for your assignment folder : ")).strip()
                if Path(new_folder_dir).is_dir():
                    print(f"Confirmarion : {new_folder_dir}")
                    confirmation = str(input("Please confirm the directory of your new assignment folder (Y/n) : "))
                    is_confirmed = False if confirmation in ["n", "N"] else True
                else:
                    print("The designated is a file path instread of a directory. File paths cannot be used as directories")
                    confirmation = str(input("Please confirm if you want to set the parent directory of your designated file path as your assignment directory (y/N) : "))
                    if confirmation in ["y", "Y"]:
                        is_confirmed = True
                        new_folder_dir = str(Path(new_folder_dir).resolve().parent)
                    else:
                        is_confirmed = False
            original_assi_folder_dir = meta_data_json[setting_capsule_name]["assi_folder_dir"]
            versioning_folder_name = f"{meta_data_json[setting_capsule_name]["capsule_name"]}_versioning"
            origial_versioning_folder_path = Path(original_assi_folder_dir) / versioning_folder_name
            meta_data_json[setting_capsule_name]["assi_folder_dir"] = new_folder_dir
            if origial_versioning_folder_path.exists():
                shutil.move(origial_versioning_folder_path, Path(new_folder_dir))
            print(f"Successfully changed to : {new_folder_dir}")

        elif setting_item_selected == "3":
            meta_data_json = self.meta_data_json
            setting_capsule_name = self.ask_capsule_name()
            print("Current Settings:")
            k = 1
            config_items = []
            for config_item in CONFIG_CONVENTION:
                origial_value = meta_data_json[setting_capsule_name]["config"][config_item]
                print(f"{k} : {config_item} ({CONFIG_CONVENTION[config_item]}) - {origial_value}")
                config_items.append(config_item)
                k += 1
            is_contuinue_to_set = True
            while is_contuinue_to_set:
                item_to_set_idx = str(input(f"Item to set (1-{k-1}): "))
                while item_to_set_idx not in [str(i) for i in range(1,k)]:
                    print("Invalid")
                    item_to_set_idx = str(input(f"Item to set (1-{k-1}): "))
                item_to_set = config_items[int(item_to_set_idx)-1]
                origial_value = meta_data_json[setting_capsule_name]["config"][item_to_set]
                if isinstance(origial_value, bool):
                    is_switch = True if str(input(f"Switch {item_to_set} from {origial_value} to {not origial_value}? (Y/n) ")) not in ["n", "N"] else False
                    if is_switch:
                        meta_data_json[setting_capsule_name]["config"][item_to_set] = not origial_value
                elif isinstance(origial_value, int):
                    new_value_to_set = input(f"Designate new value for {item_to_set} : ")
                    new_value_to_set = int(new_value_to_set) if str(new_value_to_set).isdigit() else origial_value
                    meta_data_json[setting_capsule_name]["config"][item_to_set] = new_value_to_set
                is_contuinue_to_set = False if str(input(f"Edit other settings? (y/N) ")) not in ["y", "Y"] else True

            print("Current Settings:")
            k = 1
            for config_item in CONFIG_CONVENTION:
                new_value = meta_data_json[setting_capsule_name]["config"][config_item]
                print(f"{k} : {config_item} ({CONFIG_CONVENTION[config_item]}) - {new_value}")
                k += 1
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False, indent=3)

        elif setting_item_selected == "4":
            if "app_config" in meta_data_json:
                print("Current app configurations : ")
                i = 1
                setting_item_list = []
                for app_config_item in meta_data_json["app_config"]:
                    if isinstance(meta_data_json["app_config"][app_config_item], bool):
                        print(f"{i} : {app_config_item} - {meta_data_json['app_config'][app_config_item]}")
                        setting_item_list.append(app_config_item)
                        i += 1
                is_continue_to_set = True
                while is_continue_to_set:
                    item_to_set = str(input(f"Input the item you want to set (1-{i-1}): "))
                    while item_to_set not in [f"{j}" for j in range(1,i)]:
                        print("Invalid")
                        item_to_set = str(input(f"Input the item you want to set (1-{i-1}): "))
                    meta_data_json["app_config"][setting_item_list[int(item_to_set)-1]] = not meta_data_json["app_config"][setting_item_list[int(item_to_set)-1]]
                    is_continue_to_set = False if str(input(f"Edit other app configurations? (y/N) ")) not in ["y", "Y"] else True

                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_json, f, ensure_ascii=False, indent=3)
                print("Current app configurations : ")
                for app_config_item in meta_data_json["app_config"]:
                    if isinstance(meta_data_json["app_config"][app_config_item], bool):
                        print(f"{app_config_item} - {meta_data_json['app_config'][app_config_item]}")
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
            pass

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

    mode_explanation = """Input 
    1 : continuation
    2 : versioning
    3 : initialization
    4 : settings
    5 : help"""
    print(mode_explanation)
    mode = str(input("→input : "))
    print("")

    regex_checker = re.fullmatch(r"\d[a-z|A-Z]?", mode)
    if not regex_checker:
        print("Invalid mode")
        pass
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
        print("Invalid mode")
        pass
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