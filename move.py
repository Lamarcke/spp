import json
import os.path

from config import setup_download_folder, setup_download_history
from models.history_models import DownloadHistoryEntry
from models.uploader_models import LibgenMetadata
from upload import HistoryHandler

helper = HistoryHandler()
d_h_p = setup_download_history()
up_queue = os.path.abspath(r".\upload_queue.txt")

"""
def find_where(metadata: LibgenMetadata):
    new_folder_name = helper.metadata_as_folder_name(metadata)
    new_folder_path = os.path.join(setup_download_folder(), new_folder_name)
    new_paths = []
    for path in metadata.filepaths:
        path_filename = os.path.basename(path)
        new_path = os.path.join(new_folder_path, path_filename)
        if os.path.isfile(new_path):
            new_paths.append(new_path)

    return new_paths


with open(d_h_p, "w") as down_history:
    for line in open(up_queue, "r"):
        line_strip = line.strip()
        line_as_model = LibgenMetadata(**json.loads(line_strip))
        new_filepaths = find_where(line_as_model)
        d_history_entry = DownloadHistoryEntry(metadata=line_as_model, stored_at=new_filepaths)

        down_history.write(f"{d_history_entry.json()}\n")

"""
i = []

for e in helper.get_download_history():
    i.append(e)

print(len(i))