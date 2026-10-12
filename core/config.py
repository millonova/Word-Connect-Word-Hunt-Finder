"""Persistent configuration manager for Word Hunt / Boggle Solver.

Handles reading, writing, and synchronization of config.json with auto-save hooks.
"""

import os
import json
from typing import Dict, Any, Optional
from .path_utils import get_app_dir, get_resource_path


CONFIG_PATH = os.path.join(get_app_dir(), "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "always_on_top": False,
    "overlay_always_on_top": True,
    "main_window": {
        "x": 100,
        "y": 100,
        "width": 1080,
        "height": 760
    },
    "sniper_overlay": {
        "x": 300,
        "y": 200,
        "width": 930,
        "height": 930
    },
    "scan_interval": 1.0,
    "tesseract_path": "",
    "confidence_threshold": 0.6,
    "inset_crop_ratio": 0.22,
    "overlay_visible": True
}


class AppConfig:
    """Singleton-style persistent configuration manager."""

    _instance: Optional["AppConfig"] = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._init_config(config_path)
        elif config_path is not None and os.path.abspath(config_path) != cls._instance.config_file:
            cls._instance._init_config(config_path)
        return cls._instance

    def _init_config(self, config_path: Optional[str] = None) -> None:
        self.config_file = os.path.abspath(config_path if config_path else CONFIG_PATH)
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        for k, v in saved.items():
                            if isinstance(v, dict) and k in self.data and isinstance(self.data[k], dict):
                                self.data[k].update(v)
                            else:
                                self.data[k] = v
            except Exception:
                pass
        return self.data

    def save(self) -> bool:
        """Persist configuration to disk."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Window Geometry Getters and Setters
    # -------------------------------------------------------------------------

    def get_main_window_geometry(self) -> Dict[str, int]:
        return self.data.get("main_window", DEFAULT_CONFIG["main_window"])

    def set_main_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self.data["main_window"] = {
            "x": int(x),
            "y": int(y),
            "width": max(480, int(width)),
            "height": max(400, int(height))
        }
        self.save()

    def get_sniper_overlay_geometry(self) -> Dict[str, int]:
        return self.data.get("sniper_overlay", DEFAULT_CONFIG["sniper_overlay"])

    def set_sniper_overlay_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self.data["sniper_overlay"] = {
            "x": int(x),
            "y": int(y),
            "width": max(150, int(width)),
            "height": max(150, int(height))
        }
        self.save()

    # Aliases
    def get_roi(self) -> Dict[str, int]:
        return self.get_sniper_overlay_geometry()

    def set_roi(self, x: int, y: int, width: int, height: int) -> None:
        self.set_sniper_overlay_geometry(x, y, width, height)

    # -------------------------------------------------------------------------
    # Settings Properties
    # -------------------------------------------------------------------------

    def get_always_on_top(self) -> bool:
        return bool(self.data.get("always_on_top", False))

    def set_always_on_top(self, enabled: bool) -> None:
        self.data["always_on_top"] = bool(enabled)
        self.save()

    def get_overlay_always_on_top(self) -> bool:
        return bool(self.data.get("overlay_always_on_top", True))

    def set_overlay_always_on_top(self, enabled: bool) -> None:
        self.data["overlay_always_on_top"] = bool(enabled)
        self.save()

    def get_scan_interval(self) -> float:
        return float(self.data.get("scan_interval", 1.0))

    def set_scan_interval(self, interval: float) -> None:
        self.data["scan_interval"] = max(0.2, min(5.0, float(interval)))
        self.save()

    def get_tesseract_path(self) -> str:
        configured = str(self.data.get("tesseract_path", ""))
        if configured and os.path.exists(configured):
            return configured
        bundled = get_resource_path("assets/tesseract/tesseract.exe")
        if os.path.exists(bundled):
            return bundled
        return configured

    def set_tesseract_path(self, path: str) -> None:
        self.data["tesseract_path"] = str(path)
        self.save()

    def get_inset_crop_ratio(self) -> float:
        return float(self.data.get("inset_crop_ratio", 0.22))

    def set_inset_crop_ratio(self, ratio: float) -> None:
        self.data["inset_crop_ratio"] = max(0.05, min(0.40, float(ratio)))
        self.save()

    def get_confidence_threshold(self) -> float:
        return float(self.data.get("confidence_threshold", 0.6))

    def set_confidence_threshold(self, threshold: float) -> None:
        self.data["confidence_threshold"] = max(0.1, min(1.0, float(threshold)))
        self.save()

    def get_overlay_visible(self) -> bool:
        return bool(self.data.get("overlay_visible", True))

    def set_overlay_visible(self, visible: bool) -> None:
        self.data["overlay_visible"] = bool(visible)
        self.save()
