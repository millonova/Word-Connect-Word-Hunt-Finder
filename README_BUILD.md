# Word Hunt Solver - Windows Standalone Build & Distribution Guide

This document describes how to compile the Word Hunt / Boggle Solver into a self-contained, zero-dependency Windows desktop executable (`.exe`).

End-users do **not** need to install Python, Git, or an external Tesseract OCR installer.

---

## 🚀 Quick Start: 1-Click Automated Build

To compile the standalone distribution on Windows:

1. Open File Explorer and navigate to `word_connect/`.
2. Double-click **`build_exe.bat`**.

The script will automatically:
1. Provision an isolated build environment (`build_venv`).
2. Install all pinned requirements and `pyinstaller`.
3. Verify all 26 character templates (`assets/templates/`) and the 83,500+ word dictionary.
4. Compile `main.py` using `build.spec` into an optimized `--onedir` distribution.
5. Compress the output into a ready-to-share release zip:
   ```text
   word_connect/dist/WordHuntSolver_v1.0.zip
   ```

---

## 📦 How to Distribute to End Users

1. Send `WordHuntSolver_v1.0.zip` to the user.
2. The user unzips the folder anywhere on their computer.
3. The user double-clicks **`WordHuntSolver.exe`**.

**Zero external dependencies required:**
- ✅ No Python or pip installation needed.
- ✅ No Tesseract-OCR installer needed (the app features a built-in 48x48 OpenCV template matching engine with geometric disambiguation).
- ✅ User settings and window geometry are saved locally to `config.json` next to the executable.

---

## 🛠️ Architecture & Asset Resolution

### 1. Dynamic Resource Path Resolver (`core/path_utils.py`)
Both dev environments and frozen PyInstaller packages access bundled assets through:
```python
from word_connect.core.path_utils import get_resource_path, get_app_dir

# In PyInstaller, sys._MEIPASS is automatically resolved:
template_dir = get_resource_path("assets/templates")
dictionary_path = get_resource_path("assets/words.txt")
config_file = os.path.join(get_app_dir(), "config.json")
```

### 2. Assets Included in the Executable
- **`assets/templates/`**: 26 pre-rendered, contour-bounded 48x48 binary character masks (`A.png` - `Z.png`).
- **`assets/words.txt`**: 83,500+ word tournament dictionary for instant Trie lookup.
- **`assets/tesseract/`** *(Optional)*: If portable `tesseract.exe` and `tessdata/eng.traineddata` are placed here, the engine auto-binds them as a secondary fallback.

---

## 💻 Developer Mode

To run and test the app locally in Python without compiling:

```cmd
cd word_connect
setup_dev.bat
```

Or manually:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 🧪 Verification & Automated Testing

Run the full unit test suite from the repository root:
```bash
python -m unittest discover tests
```
Tests verify template loading, geometric disambiguation algorithms (`P` vs `D`, `O` vs `D`, `E` vs `F`), Trie pathfinding, and 100% recognition on the ground-truth test board.
