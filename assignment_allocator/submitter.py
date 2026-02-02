from pathlib import Path
import json
import shutil
import os

print("Welcome to MyAssignment")
print(" ")

DAY_OF_WEEK_REF = {
    "1" : "月",
    "2" : "火",
    "3" : "水",
    "4" : "木",
    "5" : "金"
}

class MyAssigniment:
    def __init__(self):
        self.current_dir = Path(__file__).resolve().parent
        self.meta_data_path = self.current_dir / "myassi_meta.json"

    def continuation_mode(self):
        if not self.meta_data_path.exists():
            print("No default assignment folder is set")
            print("Please set default folder before using")
            return
        try:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                meta_data_json = json.load(f)
        except:
            print("No valid assignment folder is set")
            print("Please set a valid folder before using")
            return

        if len(meta_data_json) == 1:
            used_capsule_name = "default"
        else:
            k = 1
            capsule_list = []
            for capsule_name in meta_data_json:
                print(f"{k} : {capsule_name}")
                capsule_list.append(capsule_name)
                k += 1
            used_capsule = str(input("Select a capsule to use : "))
            while used_capsule not in [f"{j}" for j in range(1,k)]:
                if used_capsule_name == "": 
                    used_capsule_name = "1"
                    break
                print("Invalid")
                used_capsule = str(input("Select a capsule to use : "))
            used_capsule_name = capsule_list[int(used_capsule)-1] if used_capsule in [f"{j}" for j in range(1,k)] else "default"

        default_folder_dir = Path(meta_data_json[used_capsule_name]["assi_folder_dir"])
            
        def move_file(file_str):
            file = Path(file_str)
            print(f"Processing : {file}")
            day_of_week = str(input("Day of week of the lesson (1-5): "))
            while day_of_week not in ["1", "2", "3", "4", "5"]:
                print("Invalid")
                day_of_week = str(input("Day of week of the lesson (1-5): "))
            day_of_week = DAY_OF_WEEK_REF[day_of_week]

            dow_folder_dir = default_folder_dir / day_of_week
            if not dow_folder_dir.exists():
                dow_folder_dir.mkdir(parents=True, exist_ok=True)

            lesson_names = [f.name for f in dow_folder_dir.iterdir() if f.is_dir()]
            i = 1
            for lesson_name in lesson_names:
                print(f"{i} : {lesson_name}")
                i += 1
            print(f"{i} : Add new lesson")
            lesson_selected = str(input("Select lesson to submit : "))
            while lesson_selected not in [f"{j}" for j in range(1,i+1)] and "_" not in lesson_selected:
                print("Invalid")
                lesson_selected = str(input("Select lesson to submit : "))
            
            if lesson_selected == f"{i}":
                lesson_name_to_add = str(input("Input lesson name to add : "))
                lesson_dir_to_make = dow_folder_dir / lesson_name_to_add
                lesson_dir_to_make.mkdir(parents=True, exist_ok=True)
                lesson_names.append(lesson_name_to_add)
            
            if "_" in lesson_selected:
                lesson_selected_break = lesson_selected.split("_")
                lesson_selected = lesson_selected_break[0]
                folder_in_lesson_dir = dow_folder_dir / lesson_selected_break[-1]
                folder_in_lesson_dir.mkdir(parents=True, exist_ok=True)
                lesson_folder_dir = folder_in_lesson_dir / lesson_names[int(lesson_selected)-1]
            else:
                lesson_folder_dir = dow_folder_dir / lesson_names[int(lesson_selected)-1]

            print("-----")
            print(file)
            print(lesson_folder_dir / file_str.split("/")[-1])
            shutil.move(file, lesson_folder_dir / file_str.split("/")[-1])
            print("Successful")
                
        your_assi_path = str(input("Drag your assignment here : ")).strip()
        move_file(your_assi_path)

    def initialization_mode(self):
        print("Create new assignment capsule here")
        new_folder_dir = str(input("Input a directory for your new assignment folder : "))
        print(f"Confirmarion : {new_folder_dir}")
        confirmation = str(input("Please confirm the directory of your new assignment folder (Y/N) : "))
        is_confirmed = confirmation == "Y"
        while not is_confirmed:
            new_folder_dir = str(input("Input a directory for your new assignment folder : "))
            print(f"Confirmarion : {new_folder_dir}")
            confirmation = str(input("Please confirm the directory of your new assignment folder (Y/N) : "))
            is_confirmed = confirmation == "Y"
        
        capsule_name = str(input("Input your new capsule name : "))

        meta_data_raw = {
            "assi_folder_dir" : new_folder_dir,
            "capsule_name" : capsule_name
        }

        if not self.meta_data_path.exists():
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump({"default" : meta_data_raw}, f, ensure_ascii=False)
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
                    json.dump(meta_data_current, f, ensure_ascii=False)
                print("New capsule craeted and Set to default")
                print(f"capsule name : {capsule_name}")
                print(f"assignment folder directory : {new_folder_dir}")
            else:
                meta_data_current[capsule_name] = meta_data_raw
                with open(self.meta_data_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data_current, f, ensure_ascii=False)
                print("New capsule created")
                print(f"capsule name : {capsule_name}")
                print(f"assignment folder directory : {new_folder_dir}")

    def settings_mode(self):
        SETTING_ITEMS = {
            "1" : "change default",
            "2" : "change client folder",
            "3" : "change assignment folder"
        }
        for setting_item in SETTING_ITEMS:
            print(f"{setting_item} : {SETTING_ITEMS[setting_item]}")
        setting_item_selected = str(input("Choose a setting item : "))
        while setting_item_selected not in [f"{j}" for j in range(1,len(SETTING_ITEMS)+1)]:
            print("Invalid")
            setting_item_selected = str(input("Choose a setting item : "))

        if setting_item_selected == "2":
            print("Mode 2 has been deprecated")
            return

        if setting_item_selected == "1":
            pass
        elif setting_item_selected == "2" or setting_item_selected == "3":
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                meta_data_json = json.load(f)

            if len(meta_data_json) == 1:
                used_capsule_name = "default"
            else:
                k = 1
                capsule_list = []
                for capsule_name in meta_data_json:
                    print(f"{k} : {capsule_name}")
                    capsule_list.append(capsule_name)
                    k += 1
                used_capsule = str(input("Select a capsule to use : "))
                while used_capsule not in [f"{j}" for j in range(1,k)]:
                    if used_capsule_name == "": break
                    print("Invalid")
                    used_capsule = str(input("Select a capsule to use : "))
                used_capsule_name = capsule_list[int(used_capsule)-1] if used_capsule in [f"{j}" for j in range(1,k)] else "default" 
            
            print(f"Processing : {used_capsule_name}")

            if setting_item_selected == "2":
                new_client_dir = Path(str(input("Input new client directory : ")))
                print(f"Confirmation : {new_client_dir}")
                confirmation = str(input("Please confirm the directory of your new client folder (Y/N) : "))
                while confirmation != "Y":
                    new_client_dir = Path(str(input("Input new client directory : ")))
                    print(f"Confirmation : {new_client_dir}")
                    confirmation = str(input("Please confirm the directory of your new client folder (Y/N) : "))
                meta_data_json[used_capsule_name]["client_folder_dir"] = new_client_dir
            elif setting_item_selected == "3":
                new_assi_dir = Path(str(input("Input new assignment directory : ")))
                print(f"Confirmation : {new_assi_dir}")
                confirmation = str(input("Please confirm the directory of your new assignment folder (Y/N) : "))
                while confirmation != "Y":
                    new_client_dir = Path(str(input("Input new assignment directory : ")))
                    print(f"Confirmation : {new_assi_dir}")
                    confirmation = str(input("Please confirm the directory of your new assignment folder (Y/N) : "))
                meta_data_json[used_capsule_name]["assi_folder_dir"] = new_assi_dir
                
            print(type(meta_data_json))
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False)
        else:
            print("Invalid")
            pass


mode = str(input("Input 1 for continuation\nInput 2 for initialization\nInput 3 for settings\n→input : "))
ma = MyAssigniment()
if mode == "1":
    ma.continuation_mode()
elif mode == "2":
    ma.initialization_mode()
elif mode == "3":
    ma.settings_mode()
else:
    print("Invalid mode")
    pass