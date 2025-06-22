diff --git a/README.md b/README.md
index 97943f54cffc39f1e194f9d5d072364156ff3eaa..c89f03092d776fda14fccd2f4360e7c4475a85c8 100644
--- a/README.md
+++ b/README.md
@@ -1 +1,29 @@
-# Dust
+# Dust Audio Visualizer
+
+This repository contains a small real-time audio visualizer written in Python. It captures audio from the default system output using the `soundcard` library and displays the frequency spectrum in a Pygame window.
+Install the dependencies using the `requirements.txt` file. On Windows you can
+set up a virtual environment and install them like so:
+
+```bat
+python -m venv venv
+venv\Scripts\activate
+pip install -r requirements.txt
+```
+
+The packages listed are:
+
+```
+soundcard
+numpy
+pygame
+```
+
+## Usage
+
+Run the visualizer with:
+
+```
+python visualizer.py
+```
+
+Close the window or press `Ctrl+C` to exit.
