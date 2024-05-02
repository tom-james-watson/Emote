from setuptools import setup


setup(
    name="Emote",
    packages=["emote"],
    setup_requires=["setuptools"],
    entry_points={
        "gui_scripts": [
            "emote = emote.__init__:main",
        ]
    },
    install_requires=["setproctitle==1.3.2", "dbus-python==1.2.18"],
)
