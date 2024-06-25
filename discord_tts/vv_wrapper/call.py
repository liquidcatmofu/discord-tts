import aiohttp
import subprocess
import requests
import json
from pprint import pprint
from vv_wrapper import database as db

host = "127.0.0.1"
port = 50021


def start_engine(path: str):
    return subprocess.Popen(path, shell=True)


def vv_synthesis(text: str, speaker: int = 3, speed: float = 1.0, pitch: float = 0.0):
    params = (
        ('text', text),
        ('speaker', speaker),
    )

    # 音声合成用のクエリ作成
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params
    )
    query_json = query.json()
    query_json["speedScale"] = speed
    query_json["pitchScale"] = pitch

    # print(query.text)

    # 音声合成を実施
    synthesis = requests.post(
        f'http://{host}:{port}/synthesis',
        headers={"Content-Type": "application/json"},
        params=params,
        data=json.dumps(query_json)
    )
    return synthesis.content


class VoiceVox:
    host: str = "127.0.0.1"
    port: int = 50021
    process = None

    @classmethod
    def set_host(cls, host: str | None = None, port: int | None = None) -> None:
        if host is not None:
            cls.host = host
        if port is not None:
            cls.port = port

    @classmethod
    def synth_from_settings(cls, text: str, settings: db.BaseSetting) -> bytes:
        return cls.synthesize(
            text,
            settings.speaker,
            settings.speed,
            settings.pitch,
            settings.intonation,
            settings.volume
        )

    @classmethod
    def synthesize(
            cls,
            text: str,
            speaker: int = 3,
            speed: float = 1.0,
            pitch: float = 0.0,
            intonation: float = 1.0,
            volume: float = 1.0,
    ) -> bytes:
        if not (0.5 <= speed <= 2.0):
            raise ValueError("Speed must be between 0.5 and 2.0")
        if not (-0.15 <= pitch <= 0.15):
            raise ValueError("Pitch must be between -0.15 and 0.15")
        if not (0.0 <= intonation <= 2.0):
            raise ValueError("Intonation must be between 0.0 and 2.0")
        if not (0.0 <= volume <= 2.0):
            raise ValueError("Volume must be between 0.0 and 2.0")

        params = (
            ('text', text),
            ('speaker', speaker),
        )

        query = requests.post(f'http://{cls.host}:{cls.port}/audio_query',
                              params=params
                              )

        query_json = query.json()
        query_json["speedScale"] = speed
        query_json["pitchScale"] = pitch
        query_json["intonationScale"] = intonation
        query_json["volumeScale"] = volume
        query_json["prePhonemeLength"] = 0.0
        query_json["postPhonemeLength"] = 0.0
        query_json["outputStereo"] = False
        print(query_json)

        # 音声合成を実施
        synthesis = requests.post(
            f'http://{host}:{port}/synthesis',
            headers={"Content-Type": "application/json"},
            params=params,
            data=json.dumps(query_json)
        )

        return synthesis.content

    @classmethod
    def getspeakers(cls) -> dict:
        ret = requests.get(f'http://{cls.host}:{cls.port}/speakers')
        pprint(ret.json())
        return ret.json()

    @classmethod
    def spekerdata(cls, speaker_uuid: str) -> dict[str:str | list | dict]:
        query = {"speaker_uuid": speaker_uuid}
        ret = requests.get(f'http://{cls.host}:{cls.port}/speaker_info', params=query)
        # pprint(ret.json())
        return ret.json()


if __name__ == "__main__":
    data = VoiceVox.getspeakers()
    pprint(data)
    info = VoiceVox.spekerdata(data[0]['speaker_uuid'])
    print(info["policy"])
    # pprint(info["style_infos"])
