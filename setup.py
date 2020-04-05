from setuptools import setup, find_packages
setup(
    name="Emote",
    version="0.1.0",
    packages=['emote'],
    setup_requires=["setuptools"],
    entry_points={
        "gui_scripts": [
            "emote = emote.__init__:main",
        ]
    },
    install_requires=[
        "pygobject>=3.36.0",
        "emoji-data-python>=1.4.2"
    ]
)
