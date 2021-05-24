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

if __name__ == '__main__':
    EYESEA_ROOT = '..\\'

    json_path = os.path.join(EYESEA_ROOT, "server", "eyesea_settings.json")
    shutil.copy(
        json_path,
        json_path + ".saved"
    )

    with open(json_path, "r") as f:
        content = json.load(f)

    EYESEA_DB_PATH = content["database_storage"]

    os.system("taskkill /FI \"WindowTitle eq Front-End Server - ..\\uclient\\start_client.bat\" /T /F")
    os.system("taskkill /FI \"WindowTitle eq Back-End Server\" /T /F")
    os.system("start /min \"Front-End Server\" ..\\uclient\\start_client.bat")

    while True:
        print("\nAvailable datasets:")
        datasets = glob.glob(os.path.join(EYESEA_DB_PATH, "*.db"))
        for i, dataset in enumerate(datasets):
            print("\t{}. {}".format(i + 1, os.path.basename(dataset)))
        print("")
        print("\t{}. {}".format(len(datasets) + 1, "Ingest Stereovision Data."))
        print("\t{}. {}".format(len(datasets) + 2, "Quit"))
        
        try:
            selection = int(input("Select a dataset: ")) - 1 
        except Exception as e:
            continue

        if selection == len(datasets):
            path = input("Enter the path to Stereovision dataset (containing folders of format yyyy_mm_dd): ") 
            print("\n")
            print("\t\t********************************")
            print("\t\t** Ingesting Sterevision data **")
            print("\t\t********************************")
            os.system("python stereovision_ingest.py -d {}".format(path))
            print("\t\t******************************")
            print("\t\t**** Ingestion Completed *****")
            print("\t\t******************************")
            print("\n")
        if selection == len(datasets) + 1:
            break
        elif selection < len(datasets):
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
    # kill_process(8080)
