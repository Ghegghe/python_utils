import os
from typing import Any, Optional
import platform
import subprocess


def deep_merge(dict1: dict, dict2: dict) -> dict | None:
    """Merge two dict deeply"""
    if not dict1 and not dict2:
        return None
    if not dict1:
        return dict2
    if not dict2:
        return dict1
    merged = dict1.copy()

    for key, value in dict2.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def value_or_none(
    dict: dict, key: str, value_if_not: Any = None
) -> int | str | list | dict | Any:
    """
    Returns the dict value of the specified key if is present in the given dict,
    sobstitutive value if not (default None)
    """
    return dict[key] if key in dict else value_if_not


def run_detached_subprocess(
    command: str, subprocess_path: str, args: Optional[list] = []
) -> int:
    """
    Runs detached subprocess

    Params:
        - command (str): command to execute
        - subprocess_path (str): subprocess path
        - args (Optional[list]): args to pass

    Returns (int):
        - -2 if subprocess_path is not executable
        - -1 if subprocess_path is not a valid file
        - 0  if os is not supported
        - 1  if subprocess was successfully runned on Windows
        - 2  if subprocess was successfully runned on Darwin [macOS]
        - 3  if subprocess was successfully runned on Linux
    """
    sistema_operativo = platform.system()

    if not os.path.isfile(subprocess_path):
        return -1
    elif not os.access(subprocess_path, os.X_OK):
        return -2
    elif sistema_operativo == "Windows":
        subprocess.Popen(
            ["start", "cmd", "/c", command, subprocess_path] + args, shell=True
        )
        return 1
    elif sistema_operativo == "Darwin":  # macOS
        subprocess.Popen(["open", "-a", "Terminal", command, subprocess_path] + args)
        return 2
    elif sistema_operativo == "Linux":
        subprocess.Popen(["x-terminal-emulator", "-e", command, subprocess_path] + args)
        return 3
    else:
        return 0
