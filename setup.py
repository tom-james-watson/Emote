from setuptools import setup


setup(
    name="Emote",
    packages=['emote'],
    setup_requires=["setuptools"],
    entry_points={
        "gui_scripts": [
            "emote = emote.__init__:main",
        ]
    },
    install_requires=[
        "pygobject==3.36.0",
        "manimpango==0.3.0"
    ]
)
