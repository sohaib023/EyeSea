import os
import glob
import json
import shutil
import signal
import subprocess
from subprocess import Popen, PIPE

def kill_process(port):
    command = "netstat -ano | findstr {}".format(port)
    c = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = c.communicate()
    if len(stdout) > 0:
        pid = int(stdout.decode().strip().split(' ')[-1])
        os.kill(pid, signal.SIGTERM)

def exception_to_string(excp):
   stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=?? 
   pretty = traceback.format_list(stack)
   return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)

def process_path_input(path):
    # path = path.replace("\"", "")
    if path[0] == "\"":
        path = path[1:]
    if path[-1] == "\"":
        path = path[:-1]
    path = '\\'.join([token for token in path.split('\\') if token != ""])
    return path

if __name__ == '__main__':
    EYESEA_ROOT = '..\\'

    json_path = os.path.join(EYESEA_ROOT, "server", "eyesea_settings.json")
    shutil.copy(
        json_path,
        json_path + ".saved"
    )

    os.system("taskkill /FI \"WindowTitle eq Front-End Server - ..\\uclient\\start_client.bat\" /T /F")
    os.system("taskkill /FI \"WindowTitle eq Back-End Server\" /T /F")
    os.system("start /min \"Front-End Server\" ..\\uclient\\start_client.bat")

    while True:
        with open(json_path, "r") as f:
            content = json.load(f)

        EYESEA_DB_PATH = content["database_storage"]

        print("\nOutput directory currently being used: {}".format(os.path.dirname(content["database_storage"])))
        print("Available datasets:")
        datasets = glob.glob(os.path.join(EYESEA_DB_PATH, "*.db"))
        print("\t{}. {}".format(1, "Ingest Stereovision Data."))
        print("\t{}. {}".format(2, "Change Storage Path."))
        print("\t{}. {}".format(3, "Quit"))

        print("")
        for i, dataset in enumerate(datasets):
            print("\t{}. {}".format(i + 4, os.path.basename(dataset)))
        
        try:
            selection = int(input("Select a dataset: "))
        except Exception as e:
            print("Please enter a number.")
            continue

        if selection == 1:
            path = input("Enter the path to Stereovision dataset (containing folders of format yyyy_mm_dd): ") 
            path = process_path_input(path)

            print("\n")
            print("\t\t********************************")
            print("\t\t** Ingesting Sterevision data **")
            print("\t\t********************************")
            os.system("python stereovision_ingest.py -d \"{}\"".format(path))
            print("\t\t******************************")
            print("\t\t**** Ingestion Completed *****")
            print("\t\t******************************")
            print("\n")
        elif selection == 2:
            path = input("Enter the path to be used for EyeSea data storage: ") 
            path = process_path_input(path)

            try:
                os.makedirs(path, exist_ok=True)
            except:
                print(exception_to_string(e))
                continue

            with open(json_path, "r") as f:
                content = json.load(f)
            content["cache"]                 = os.path.join(path, os.path.basename(content["cache"]))
            content["temporary_storage"]     = os.path.join(path, os.path.basename(content["temporary_storage"]))
            content["video_storage"]         = os.path.join(path, os.path.basename(content["video_storage"]))
            content["database_storage"]      = os.path.join(path, os.path.basename(content["database_storage"]))
            content["video_overlay_storage"] = os.path.join(path, os.path.basename(content["video_overlay_storage"]))
            content["csv_storage"]           = os.path.join(path, os.path.basename(content["csv_storage"]))
            with open(json_path, "w") as f:
                f.write(json.dumps(content, indent=4))
            print("Storage path successfully changed to: {}".format(path))
        elif selection == 3:
            break
        else:
            selection -= 4
            if selection < len(datasets):
                dataset = datasets[selection]
                with open(json_path, "r") as f:
                    content = json.load(f)
                content["database"] = os.path.basename(dataset)
                with open(json_path, "w") as f:
                    f.write(json.dumps(content, indent=4))

                # kill_process(8080)
                os.system("taskkill /FI \"WindowTitle eq Back-End Server\" /T /F")

                os.system("start /min \"Back-End Server\" python eyesea_server.py")
                os.system("start http://localhost:7890")
            else:
                continue

    print("Killing")
    os.system("taskkill /FI \"WindowTitle eq Front-End Server - ..\\uclient\\start_client.bat\" /T /F")
    os.system("taskkill /FI \"WindowTitle eq Back-End Server\" /T /F")