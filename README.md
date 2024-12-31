# Helper script for importing images exported from Google Photos (via Google Takeout) into Photos app in macOS

When I tried to import photos downloaded from Google Takeout into ***Photos*** app in macOS, the original date of photos are messed up! Somehow, Photos app used the creation date of each photo (which appears to be a date each file was added into the archive) to manage photo's date although the photo's original date is existed in that photo's EXIF metadata.

Luckily, Google Takeaway gave us timestamp of both `creationTime` and `photoTakenTime` in each photo's JSON file.

This script, written in Python, tries to read `photoTakenTime` timestamp from JSON file and set is as that file's creation date instead. This way, photo's date in ***Photos*** app will be displayed correctly, *as it should be*.

Also, there are so many duplicates as Google exported photos grouped by Year, Album, Archive/Trash. This script can also merge all photos from extracted folders into single folder as well.

## Required python modules

* Standard modules: `os`, `json`, `datetime` and `argparse`
* `exif` module which can be installed via `pip` using `pip install exif`

## Recommended steps

1. Unarchive files downloaded from Google Takeout and put that folders in the same directory
2. From that top directory (will be referred as `DIR`), run this command to modify all photo's `mtime` and `atime` using timestamp from JSON file or EXIF key respectively:

   ```terminal
   python3 gg-takeout-postprocess.py DIR --merge MERGED_OUTPUT_DIR
   ```

   A script will merge all photos and JSON files into `MERGED_OUTPUT_DIR` first and then try to find a JSON file corresponds to each photo first. If found, script will get a timestamp from `photoTakenTime.timestamp` key and set `mtime` and `atime` of that file to this timestamp.

   If JSON file is not found, script will try to get photo's original datetime from EXIF key named `datetime_original`, convert to timestamp and apply it to `mtime` and `atime` of that file.

   If a target EXIF key is still not exist, that photo is left unchanged.

   This script will be run recursively to all files (which is not `.*` like `.DS_Store`, JSON and HTML files) and folders in `DIR`.

   These optional arguments can also be used:

   * `--update`: `mtime` and `atime` will be changed for every photos whose `mtime` differs from timestamp specified in JSON file or EXIF key only
   * `--remove-json`: JSON file will be deleted if timestamp is get successfully
   * `--log LOG_FILENAME`: Enable logging and write to `LOG_FILENAME`
   * `--verbose`: Enable verbosing

3. When script is finished, `mtime` and `atime` of photos will be updated and you can import them into `Photos` app wihout having a headache with photo's datetime issues! (At least, for most of them)
