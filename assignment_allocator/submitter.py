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
    "5" : "金",
    "6" : "土",
    "7" : "日"
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

class MyAssigniment:
    def __init__(self):
        self.current_dir = Path(__file__).resolve().parent
        self.meta_data_path = self.current_dir / "myassi_meta.json"
        if not self.meta_data_path.exists():
            print("No default assignment folder is set")
            print("Please set default folder before using")
            return
        try:
            with open(self.meta_data_path, "r", encoding="utf-8") as f:
                self.meta_data_json = json.load(f)
        except:
            print("No valid assignment folder is set")
            print("Please set a valid folder before using")
            return
        
    def ask_capsule_name(self):
        if len(self.meta_data_json) == 1:
            used_capsule_name = "default"
        else:
            k = 1
            capsule_list = []
            for capsule_name in self.meta_data_json:
                print(f"{k} : {capsule_name}")
                capsule_list.append(capsule_name)
                k += 1
            used_capsule = str(input("Select a capsule: "))
            while used_capsule not in [f"{j}" for j in range(1,k)]:
                if used_capsule_name == "": 
                    used_capsule_name = "1"
                    break
                print("Invalid")
                used_capsule = str(input("Select a capsule: "))
            used_capsule_name = capsule_list[int(used_capsule)-1] if used_capsule in [f"{j}" for j in range(1,k)] else "default"
        return used_capsule_name

    def continuation_mode(self):
        meta_data_json = self.meta_data_json

        used_capsule_name = self.ask_capsule_name()

        capsule_root_folder_dir = Path(meta_data_json[used_capsule_name]["assi_folder_dir"])
            
        def move_file(file_str):
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
                target_names = [f.name for f in searching_folder_dir.iterdir() if f.is_dir()]
                i = 1
                for target_name in target_names:
                    print(f"{i} : {target_name}")
                    i += 1
                print(f"{i} : Add new lesson")
                target_selected = str(input("Select lesson to submit : "))
                while target_selected not in [f"{j}" for j in range(1,i+1)] and "_" not in target_selected:
                    print("Invalid")
                    target_selected = str(input("Select lesson to submit : "))
                
                if target_selected == f"{i}":
                    target_name_to_add = str(input("Input lesson name to add : "))
                    target_dir_to_make = searching_folder_dir / target_name_to_add
                    target_dir_to_make.mkdir(parents=True, exist_ok=True)
                    target_names.append(target_name_to_add)
                
                if "_" in target_selected:
                    try:
                        target_selected_break = target_selected.split("_")
                        target_selected = target_selected_break[0]
                        searching_folder_dir = searching_folder_dir / target_names[int(target_selected)-1]
                        searching_folder_dir = searching_folder_dir / target_selected_break[-1]
                        searching_folder_dir.mkdir(parents=True, exist_ok=True)
                    except:
                        print("Invalid Input")
                        return
                else:
                    searching_folder_dir = searching_folder_dir / target_names[int(target_selected)-1]
                
                searching_layer += 1

            target_folder_dir = searching_folder_dir
            print("-----")
            print(file)
            print(target_folder_dir / file_str.split("/")[-1])
            shutil.move(file, target_folder_dir / file_str.split("/")[-1])
            print("Successful")
                
        your_assi_path = str(input("Drag your assignment here : ")).strip()
        move_file(your_assi_path)

    def initialization_mode(self, config_conversation=False):
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
            "capsule_name" : capsule_name,
            "config": CONFIG
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
            
            if config_conversation:
                is_use_weekday = True if str(input("Use the weekday based allocation system? (Y/n)")) not in ["n", "N"] else False
                is_include_weekends = False if str(input("Include weekends in your file system? (y/N)")) not in ["y", "Y"] else True
                dive_layer = input("Designate the number of dive layer")
                dive_layer = int(dive_layer) if str(dive_layer).isdigit() == True else 1
                config_items_list = [config_item for config_item in CONFIG]
                config_dic = {
                    config_items_list[0]: is_use_weekday,
                    config_items_list[1]: is_include_weekends,
                    config_items_list[2]: dive_layer
                } #"use_weekday", "include_weekends", "dive_layer"
                meta_data_raw["config"] = config_dic

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
            "3" : "change assignment folder", 
            "4" : "edit configurations"
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
                
            with open(self.meta_data_path, "w", encoding="utf-8") as f:
                json.dump(meta_data_json, f, ensure_ascii=False)

        elif setting_item_selected == "4":
            meta_data_json = self.meta_data_json
            setting_capsule_name = self.ask_capsule_name()
            print("Current Settings:")
            k = 1
            config_items = []
            for config_item in CONFIG_CONVENTION:
                origial_value = meta_data_json[setting_capsule_name]["config"][config_item]
                print(f"{k} : {config_item} ({CONFIG_CONVENTION[config_item]}) - {origial_value}")
                config_items.append(config_item)
                k + 1
            is_contuinue_to_set = True
            while is_contuinue_to_set:
                item_to_set_idx = str(input(f"Day of week of the lesson (1-{k-1}): "))
                while item_to_set_idx not in [str(i) for i in range(1,k)]:
                    print("Invalid")
                    item_to_set_idx = str(input(f"Day of week of the lesson (1-{k-1}): "))
                item_to_set = config_items[int(item_to_set_idx)-1]
                origial_value = meta_data_json[setting_capsule_name]["config"][item_to_set]
                if isinstance(origial_value, bool):
                    is_switch = True if str(input(f"Switch {item_to_set} from {origial_value} to {not origial_value}? (Y/n)")) not in ["n", "N"] else False
                    if is_switch:
                        meta_data_json[setting_capsule_name]["config"][item_to_set] = not origial_value
                is_contuinue_to_set = False if str(input(f"Edit other settings? (y/N)")) not in ["y", "Y"] else True
            print("Current Settings:")
            for config_item in CONFIG_CONVENTION:
                new_value = meta_data_json[setting_capsule_name]["config"][config_item]
                print(f"{k} : {config_item} ({CONFIG_CONVENTION[config_item]}) - {new_value}")
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
elif mode == "2i":
    ma.initialization_mode(config_conversation=True)
elif mode == "3":
    ma.settings_mode()
else:
    print("Invalid mode")
    pass