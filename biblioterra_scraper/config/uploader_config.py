import os


def setup_uploaded_files_log():
    uploaded_files_log = os.environ.get("UPLOAD_QUEUE_FILE")
    if uploaded_files_log is None:
        uploaded_files_log = os.path.abspath(rf".\uploaded_files.txt")

    uploaded_files_log.encode(encoding="UTF-8")

    if not os.path.isfile(uploaded_files_log):
        c = open(uploaded_files_log, "w")

    return uploaded_files_log


def setup_upload_queue_log():
    upload_queue_file = os.environ.get("UPLOAD_QUEUE_FILE")

    if upload_queue_file is None:
        upload_queue_file = os.path.abspath(rf".\upload_queue.txt")

    upload_queue_file.encode(encoding="UTF-8")
    if not os.path.isfile(upload_queue_file):
        c = open(upload_queue_file, "w")

    return upload_queue_file
