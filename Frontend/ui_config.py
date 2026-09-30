"""UI constants passed to the Jinja template (icons are shared with static/app.js via window.ICONS)."""

APP_NAME = "TVS Capital"
LOGO_FILE = "TCF-Logo-Primary.svg"   # file inside Frontend/images/

ICONS = {
    "plus": "M12 5v14M5 12h14",
    "file": "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h6",
    "trash": "M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14",
    "panel": "M4 4h16v16H4zM15 4v16",
    "spark": "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z",
    "search": "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4",
    "arrow": "M5 12h14M13 6l6 6-6 6",
    "close": "M6 6l12 12M18 6L6 18",
    "menu": "M4 7h16M4 12h16M4 17h16",
    "chart": "M3 20h18M6 16v-5M11 16V6M16 16v-8",
    "shield": "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
    "external": "M14 4h6v6M20 4l-9 9M18 14v5H5V6h5",
    "copy": "M9 9h11v11H9zM5 15V4h11",
}

PROMPTS = [
    {"icon": "file", "title": "Compare investment notes",
     "prompt": "What changed between the original IC note and the top-up IC note for InsuranceDekho?"},
    {"icon": "shield", "title": "Review key risks",
     "prompt": "What were the key risks highlighted in the InsuranceDekho due diligence report?"},
    {"icon": "chart", "title": "Check performance",
     "prompt": "What is the latest reporting period for Yubi and what does it say about performance?"},
    {"icon": "search", "title": "Find documents",
     "prompt": "Which documents mention Fund-3, and what topics do they cover?"},
]