from logging import getLogger
from subprocess import Popen, DEVNULL, PIPE

logger = getLogger(__name__)

def start_engine(path_arguments: str) -> Popen:
    logger.info(f"Starting VoiceVox engine with {path_arguments}")
    process = Popen(path_arguments, shell=True, stdout=PIPE, stderr=DEVNULL, text=True)
    while True:
        output = process.stdout.readline()
        if "100%" in output:
            break
    logger.info("VoiceVox engine started")
    return process
