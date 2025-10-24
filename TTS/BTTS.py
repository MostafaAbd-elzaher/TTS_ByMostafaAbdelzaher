"""Compatibility wrapper to import the implementation from BTTS.PY.

On some filesystems (Linux) a file named 'BTTS.PY' is not found by
`import BTTS` because Python looks for 'BTTS.py'. This wrapper loads the
BTTS.PY file by path and re-exports the main symbols the GUI expects.
"""
import os
import runpy

HERE = os.path.dirname(__file__)
alt_path = os.path.join(HERE, "BTTS.PY")

if not os.path.exists(alt_path):
    raise ImportError(f"Could not find BTTS.PY at {alt_path}")

# Execute BTTS.PY in its own namespace and re-export expected symbols
ns = runpy.run_path(alt_path)
create_emotional_tts = ns.get("create_emotional_tts")
available_emotions = ns.get("available_emotions")
if create_emotional_tts is None or available_emotions is None:
    raise ImportError("BTTS.PY does not define the expected symbols.")
__all__ = ["create_emotional_tts", "available_emotions"]
