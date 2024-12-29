import sys
from subprocess import Popen, DEVNULL, PIPE

def start_engine(path_arguments: str) -> Popen:
    print("Starting VoiceVox engine...")
    process = Popen(path_arguments, shell=True, stdout=PIPE, stderr=DEVNULL, text=True)
    while True:
        output = process.stdout.readline()
        # sys.stdout.write(output)
        if "100%" in output:
            break
    return process
