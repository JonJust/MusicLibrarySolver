from setuptools import setup, find_packages

setup(
    name="music_stats",
    version="1.0.0",
    author="My Name",
    description="A tool for organizing large music libraries and splitting .cue files",
    packages=["music_stats"],
    install_requires=[
        "ffmpeg-python",
        "mutagen",
        "tqdm"
    ],
    entry_points={
        "console_scripts": [
            "cue-splitter=music_stats.cue_splitter:main",
            "music-stats=music_stats.music_stats:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.7',
)
