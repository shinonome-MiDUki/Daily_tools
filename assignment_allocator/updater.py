import subprocess
import os
import shutil
import sys

def update_from_git(current_dir, my_path):
    git_url = "https://github.com/shinonome-MiDUki/Daily_tools.git"
    storing_dir = current_dir / "for_git_clone_update"
    storing_dir.mkdir(parents=True)
    try:
        subprocess.run(["git", "clone", git_url, storing_dir], check=True)
    except:
        print("Github cloning error")
        return
    updated_script_dir = storing_dir / "assignment_allocator"
    dot_git_folder_dir = updated_script_dir / ".git"
    try:
        py_major_version = int(sys.version.split(".")[0])
        py_minor_version = int(sys.version.split(".")[1])
        def untrack_git_error(func, path, excinfo):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        if py_major_version == 3 and py_minor_version >= 12:
            shutil.rmtree(dot_git_folder_dir, onexc=untrack_git_error)
        else:
            shutil.rmtree(dot_git_folder_dir, onerror=untrack_git_error)
        files_to_delete = ["myassi_meta.json", "updater.py", "test.py"]
        for file_to_delete in files_to_delete:
            default_json_config_path = updated_script_dir / file_to_delete
            if default_json_config_path.exists():
                os.unlink(updated_script_dir / "myassi_meta.json")
        shutil.move(updated_script_dir / "submitter.py", current_dir / "update_submitter.py")
    except:
        print("Git history clearing error")
        return
    try:
        updated_script_dir.rmdir()
        storing_dir.rmdir()
    except:
        print("Unable to clear empty folder")
    try:
        os.unlink(my_path)
        os.rename(current_dir / "update_submitter.py", current_dir / "submitter.py")
    except:
        print("Renaming failed")
        return
    print("Update succeed")