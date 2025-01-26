from setuptools import setup

setup(
    name="discord_tts",
    version="0.1.0",
    description="Discord Text to Speech bot",
    requires=["py-cord", "python-dotenv", "PyNaCl", "requests", "google-re2"],
    packages=["discord_tts"],
    entry_points={
        "console_scripts": [
            "discord_tts = discord_tts.__main__:main"
        ]
    }
)
