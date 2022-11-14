import os


def setup_temp_download_folder() -> str:
    temp_download_folder = os.environ.get("TEMP_DOWNLOAD_FOLDER")

    if not temp_download_folder:
        temp_download_folder = os.path.abspath(r".\data\temp")

    temp_download_folder.encode(encoding="UTF-8")

    if not os.path.isdir(temp_download_folder):
        os.mkdir(temp_download_folder)

    return temp_download_folder


def setup_download_folder() -> str:
    download_folder = os.environ.get("DOWNLOAD_FOLDER")

    if not download_folder:
        download_folder = os.path.abspath(r".\data\downloads")

    download_folder.encode(encoding="UTF-8")

    if not os.path.isdir(download_folder):
        os.mkdir(download_folder)
    return download_folder


def setup_upload_history():
    upload_history_file = os.path.abspath(rf".\upload_history.txt")

    upload_history_file.encode(encoding="UTF-8")

    if not os.path.isfile(upload_history_file):
        c = open(upload_history_file, "w")

    return upload_history_file


def setup_download_history():

    upload_history_file = os.path.abspath(rf".\download_history.txt")

    upload_history_file.encode(encoding="UTF-8")

    if not os.path.isfile(upload_history_file):
        c = open(upload_history_file, "w")

    return upload_history_file
