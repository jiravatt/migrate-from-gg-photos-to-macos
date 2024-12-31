import argparse, os, json, datetime, exif

#### ARGUMENT BUILDER & PARSER ####

argparser = argparse.ArgumentParser()
argparser.add_argument("dir", type=str, help='an absolute path to the extracted folder from Google Takeout archive')
argparser.add_argument("--merge", type=str, help="merge folders into specified path")
argparser.add_argument("--update", action="store_true", help="set timestamp only if file's timestamp is different from json or exif")
argparser.add_argument("--remove-json", action="store_true", help="remove JSON file after it has been used")
argparser.add_argument("--verbose", action="store_true", help='print log on screen')
argparser.add_argument("--log", type=str, help='write logs to a file of given name in current directory')


#### HELPER FUNCTIONS ####

def prog_output(txt: str):
    if args.log:
        log_stream.write(txt)
    if args.verbose:
        print(txt, end='')


def json_filename_list(file):
    original_filename = os.path.basename(file)
    dir_path = os.path.dirname(file)

    original_pure_filename = '.'.join(original_filename.split('.')[:-1])
    original_ext = original_filename.split('.')[-1]

    # If principal part of filename is empty (like .DS_STORE), return nothing
    if not original_pure_filename:
        return []

    filename_list = []

    # FIRST CASE: add '.json' into filename (majority)
    filename_list.append(original_filename + '.json')

    # SECOND CASE: replace ext with 'json'
    filename_list.append(original_pure_filename + '.json')

    # THIRD CASE: if filename (without ext part) ends with _, removes it and add/replace with '.json'
    # (UPDATE: last char of principal filename is dropped)
    filename_list.append(original_pure_filename[:-1] + '.json')
    filename_list.append(original_pure_filename[:-1] + '.' + original_ext + '.json')
    
    # FOURTH CASE: if filename ends with (1), moves (1) after ext and append '.json'
    if original_pure_filename[-3:] == '(1)':
        filename_list.append(original_pure_filename[:-3] + '.' + original_ext + '(1)' + '.json')
        filename_list.append(original_pure_filename[:-4] + '(1).json')

    # FIFTH CASE: double periods before file's extension
    if original_filename.split('.')[-2] == '':
        filename_list.append('.'.join(original_filename.split('.')[:-2]) + '.json')
        filename_list.append('.'.join(original_filename.split('.')[:-2]) + '.' + original_ext + '.json')

    # INSERT DIR_PATH IN FRONT OF EACH FILENAME
    filename_list_final = list(map(lambda fn: os.path.join(dir_path, fn), filename_list))
    
    return filename_list_final


#### RECURSIVE FUNCTIONS ####

def recursive_merge(working_dir):
    # get list of all items in a directory
    dir_items = list(map(lambda item: os.path.join(working_dir, item), os.listdir(working_dir)))
    
    for sub_dir in list(filter(os.path.isdir, dir_items)):
        # recursives into each dir
        recursive_merge(sub_dir)

    # get list of all image files and its corresponding json needed to be moved into new dir
    file_list = list(filter(lambda f: os.path.isfile(f)
                            * os.path.basename(f).split(".")[0]
                            * (os.path.basename(f).split(".")[-1] != "html")
                            * (not ((os.path.basename(f).split('.')[0][:8] == 'metadata') and (os.path.basename(f).split(".")[-1] == "json")))
                            , dir_items))
    
    # if no files is found, end this function
    if not file_list:
        return None

    # move all files into target dir
    for file in file_list:
        file_new_dest = os.path.join(merge_target_dir, os.path.basename(working_dir), os.path.basename(file))

        move_action = False
        if os.path.isfile(file_new_dest):
            if input(f"Rewrite {file_new_dest} with {file} ? [y/N]: ").lower() == 'y':
                move_action = True
        else:
            move_action = True
        
        if move_action:
            os.renames(file, file_new_dest)
            prog_output(f"MOVED: {file} -> {file_new_dest}\n")


def recursive_set_date(dir):
    dir_items = list(map(lambda item: os.path.join(dir, item), os.listdir(dir)))
    
    for sub_dir in list(filter(os.path.isdir, dir_items)):
        recursive_set_date(sub_dir)
    
    # For each files (which isn't json), read json for creationTime's timestamp and set it as file's created time
    for file in list(filter(lambda f: os.path.isfile(str(f))
                            * (not str(f).split('.')[-1] in ['json', 'html'])
                            * os.path.basename(f).split('.')[0]
                            , dir_items)):
        
        # Get file's original modification time
        file_original_timestamp = int(os.stat(file).st_mtime)

        # Target mtime
        file_new_timestamp = None

        # Try to get timestamp from JSON file first
        for json_file in json_filename_list(file):
            if os.path.isfile(json_file):
                with open(json_file, 'r') as jf:
                    file_new_timestamp = int(json.load(jf).get('photoTakenTime').get('timestamp'))
                    file_new_timestamp_src = 'JSON'
                if args.remove_json:
                    os.remove(json_file)
                    prog_output(f"DELETED: {json_file}\n")
                break

        # If JSON file does not exist, read from exif
        if not file_new_timestamp:
            try:
                ts_date, ts_time = list(map(lambda dt: list(map(int, dt.split(':'))), exif.Image(file).get('datetime_original').split(' ')))
                file_new_timestamp = datetime.datetime(ts_date[0], ts_date[1], ts_date[2], ts_time[0], ts_time[1], ts_time[2]).timestamp()
                file_new_timestamp_src = 'EXIF'
            except:
                file_new_timestamp_src = None

        # Skip when no changes to be made
        if (file_new_timestamp_src is None):
            prog_output(f"SKIPPED: {file} ... Timestamp NOT FOUND.\n")
            continue
        elif args.update and (file_original_timestamp == file_new_timestamp):
            prog_output(f"SKIPPED: {file} ... Timestamp OK.\n")
            continue
        
        # Set or update access and modification time
        file_new_datetime = datetime.datetime.fromtimestamp(file_new_timestamp)        
        os.utime(file, (file_new_timestamp, file_new_timestamp))
        prog_output(f"SET: {file} => {file_new_datetime.strftime("%Y:%m:%d %H:%M:%S")} ({file_new_timestamp_src})\n")
        

## MAIN PROGRAM STARTS HERE ##

# Fetch arguments
args = argparser.parse_args()

# If logging is enabled, open stream for writing a log file
if args.log:
    log_file_path = os.path.abspath(args.log)
    log_stream = open(log_file_path, "w")

# For merging process, create target dir if not exist and merge recursively if merge option is specified
if args.merge:
    merge_target_dir = os.path.abspath(args.merge)
    os.makedirs(merge_target_dir, exist_ok=True)

    recursive_merge(args.dir)

    recursive_set_date(merge_target_dir)

else:
    # Set mtime and atime recursively
    recursive_set_date(args.dir)

# close logging stream
if args.log:
    log_stream.close()
