import os


def setup_upload_history():
    upload_history_file = os.environ.get("UPLOAD_HISTORY_FILE")
    if upload_history_file is None:
        upload_history_file = os.path.abspath(rf".\upload_history.txt")

    upload_history_file.encode(encoding="UTF-8")

    if not os.path.isfile(upload_history_file):
        c = open(upload_history_file, "w")

    return upload_history_file


def setup_upload_queue():
    upload_queue_file = os.environ.get("UPLOAD_QUEUE_FILE")

    if upload_queue_file is None:
        upload_queue_file = os.path.abspath(rf".\upload_queue.txt")

    upload_queue_file.encode(encoding="UTF-8")
    if not os.path.isfile(upload_queue_file):
        c = open(upload_queue_file, "w")

    return upload_queue_file
