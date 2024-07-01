from setuptools import setup

setup(
    name="discord_tts",
    version="0.0.1",
    description="Discord Text to Speech bot",
    requires=["py-cord", "python-dotenv", "PyNaCl", "requests"],
    packages=["discord_tts"],
    entry_points={
        "console_scripts": [
            "discord_tts = discord_tts.__main__:main"
        ]
    }
)
