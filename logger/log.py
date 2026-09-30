"""Coloured console tracing so you can watch the graph run."""
import json
import os
from termcolor import colored

os.system("")  # enables ANSI colours in the Windows console


def banner(text: str):
    line = "=" * 78
    print(colored(f"\n{line}\n{text}\n{line}", "magenta", attrs=["bold"]))


def node(name: str):
    print(colored(f"\n>> NODE: {name}", "cyan", attrs=["bold"]))


def info(msg: str):
    print(colored(f"   - {msg}", "white"))


def ok(msg: str):
    print(colored(f"   [OK] {msg}", "green"))


def warn(msg: str):
    print(colored(f"   [WARN] {msg}", "yellow"))


def err(msg: str):
    print(colored(f"   [ERR] {msg}", "red", attrs=["bold"]))


def data(label: str, value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, indent=2, ensure_ascii=False)
    print(colored(f"   {label}: ", "blue", attrs=["bold"]) + colored(str(value), "light_grey"))
