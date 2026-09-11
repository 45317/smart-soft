"""
PyInstaller build script for SmartSoft.
Run this to create the exe distribution.
"""
import os
import subprocess
import sys
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")


def clean():
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SmartSoft",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--add-data=project;project",
        "--add-data=products;products",
        "--add-data=pages;pages",
        "--add-data=rag;rag",
        "--add-data=config.ini;.",
        "--hidden-import=django",
        "--hidden-import=django.contrib.admin",
        "--hidden-import=django.contrib.auth",
        "--hidden-import=django.contrib.contenttypes",
        "--hidden-import=django.contrib.sessions",
        "--hidden-import=django.contrib.messages",
        "--hidden-import=django.contrib.staticfiles",
        "--hidden-import=pages",
        "--hidden-import=products",
        "--hidden-import=rag",
        "--hidden-import=rag.embeddings",
        "--hidden-import=rag.llm",
        "--hidden-import=rag.storage",
        "--hidden-import=rag.documents",
        "--hidden-import=rag.pipeline",
        "--hidden-import=psycopg2",
        "--hidden-import=faiss",
        "--hidden-import=sentence_transformers",
        "--hidden-import=transformers",
        "--hidden-import=torch",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--collect-all=django",
        "--collect-all=sentence_transformers",
        "--collect-all=transformers",
        "--collect-all=torch",
        "--collect-all=faiss",
        "--collect-all=pystray",
        "--collect-all=PIL",
        "--collect-all=psycopg2",
        "launcher.py",
    ]

    print("Building SmartSoft exe...")
    print("This may take 5-10 minutes...")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    print("Build successful!")
    print(f"Output: {os.path.join(DIST_DIR, 'SmartSoft')}")


if __name__ == "__main__":
    clean()
    build()
