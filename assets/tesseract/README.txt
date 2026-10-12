Portable Tesseract Binaries Directory
======================================
This directory holds optional portable Tesseract binaries for self-contained Windows deployment.

Structure:
  word_connect/assets/tesseract/
    ├── tesseract.exe
    └── tessdata/
        └── eng.traineddata

Note:
The Word Connect / Word Hunt solver includes a high-accuracy Template Matching engine
that functions autonomously even without Tesseract installed. If tesseract.exe is present here,
the app will automatically use it as an enhanced fallback recognition pass.
