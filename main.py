import os
import re
import sys
import time
import shutil

try:
    import psutil
except ImportError():
    print("Missing package 'psutil', install it by running",
          "\n\t`pip install psutil` from a console, and try again")

def main():

    #
    # Step 1.
    #   Collect photo files references from argument (directory),
    #   report basic findings, and prompt for where to write to
    #

    # Validate and use passed argument as source path root
    pd = PhotoDrive(sys.argv)
    base_read_path = pd.root_dir

    # Report where we're reading from
    print(f"Reading from the directory '{base_read_path}' (will look for JPG:NEF pairs here)")

    # Report number of photos found
    print(f"Found {len(pd.jpgs)} JPEGs, {len(pd.nefs)} NEFs in this directory")

    # Prompt for which drive to write to
    drive_list_str = ''
    drive_list_cnt = len(pd.indexed_mountpoints) - 1
    for i, d in pd.indexed_mountpoints.items():
        print(f"[{i}]\t{d.mountpoint}")

    # Get drive we'll be writing our results to, or just bail
    input_disk_idx = prompt(msg ="Select (from above numbers) which drive to write paired images to",
                            opts="0 to "+str(drive_list_cnt))

    if not input_disk_idx or int(input_disk_idx) > drive_list_cnt:
        prompt(msg        = f"Error: You must select a write drive (between 0 and {drive_list_cnt})",
               opts       = "Enter to exit",
               exit_after = True)

    # All's well, cast to int for get
    input_disk_idx = int(input_disk_idx)

    # Path to write out paired files to same-named output dir as input dir, on chosen volume
    write_dir = os.path.join(pd.indexed_mountpoints.get(input_disk_idx).mountpoint,
                             "out",
                             pd.root_dir.split(os.sep)[-1])

    # Create output dir if it doesn't already exist
    if not os.path.isdir(write_dir):
        os.makedirs(write_dir)

    elif len(os.listdir(write_dir)) > 1:
        prompt(msg=f"WARNING: '{write_dir}' already contains files - "+
                   "are you sure you want overwrite these?",
               opts="Enter to continue")

    # Init our simple report class (will write operation results to this file)
    r = Report(os.path.join(write_dir, "REPORT.log"))
    r.write_line(f"Input  Directory: {base_read_path} (looking for pairs here)")
    r.write_line(f"Output Directory: {write_dir} (will write pairs to here)")
    r.write_line(f"{len(pd.jpgs)} JPEGs, {len(pd.nefs)} NEFs found in Input Directory")

    #
    # Step 2.
    #   Reports on photo pairs found in given directory, and copy to given write path
    #

    # Match up JPG:NEF files, report
    photo_pairs = pd.pair_photos()
    r.write_line(f"{len(photo_pairs)} JPG to NEF file matching pair(s) found in Input Directory")

    # Report on JPGs which no corresponding NEF file could be found
    for orphan_jpg in pd.pair_photos(reverse=True):
        r.write_line(f"WARNING: could not find NEF file for '{orphan_jpg}' !!!")

    prompt(msg="Ready to start copying over files",
           opts="Enter to proceed")

    #
    # XXX Investigate: Is meta-data lost in copy operation ?
    #

    #
    # XXX BUG: Will overwrite files of the same name
    #   Prompt? Warn? What do?
    #
    for jpg, nef in photo_pairs:

        try:
            result = safe_copy(jpg, write_dir)
            r.write_line(result)
        except Exception as e:
            r.write_line(str(e))

        result = ''

        try:
            result = safe_copy(nef, write_dir)
            r.write_line(result)
        except Exception as e:
            r.write_line(str(e))


    # All done - notify and exit
    prompt(msg="Done.", opts="Enter to exit")
    r.write_line(f"Program terminated normally\n"+("-"*80))

def safe_copy(src, dst):
    """ Check if :dst: dir already had a file which matches :src:'s file name
    Returns a report string of the operation performed. """

    # Sentinal to detect whether we've overwritten a file
    overwrite = False

    # Grab source file name
    src_file = src.split(os.sep)[-1]

    # Basic checks to ensure this is a valid operation
    if not os.path.isfile(src):
        raise Exception(f"'{src}' is not a file")
    if not os.path.isdir(dst):
        raise Exception(f"'{dst}' is not a directory")

    # Check if file of this name exists at destination
    if os.path.isfile(os.path.join(dst, src_file)):
        #raise Exception(f"File named {src_file} already exists in {dst}")
        overwrite = True

    shutil.copy(src, dst)

    op_str = str(right_pad(f"copied '{src}'", padding=80)
                 + right_pad("to", padding=4)
                 + right_pad(f"'{dst+os.sep+src_file}'", padding=10))

    # Notify if we've overwritten a file
    if overwrite:
        op_str += " (OVERWRITTEN)"

    return op_str

def prompt(msg, opts, exit_after=False):
    """ Print :msg: and input :opts: to terminal, and optionally :after_after: user input received """
    user_input = input(f"{str(msg)} [{str(opts)} (q to quit)] >>> ")

    # Quit if specified in invocation, or user input
    if user_input.lower() == 'q' or exit_after:
        print("Bye")
        exit(1)

    return user_input

def right_pad(s='', padding=20, padding_char=' '):
    """ Returns the given :s:tr, padded on the right by 0 to [padding] [padding_char] chars """
    padded_str = s  # Safe default in case of 0, or negative padding
    for i in range(len(s), padding):
        padded_str += padding_char

    return padded_str


class PhotoDrive():
    def __init__(self, args):

        # Check if we were passed a root dir to operate on
        if len(args) < 2:
            prompt(msg        = "Error: script must be run with root directory (year, eg: '2017')",
                   opts       = "Enter to exit",
                   exit_after = True)

        # Check viability of root dir
        root_dir = args[1]
        if not os.path.isdir(root_dir):
            prompt(msg        = f"Error: '{os.path.abspath(root_dir)}' is not a valid directory",
                   opts       = "Enter to exit",
                   exit_after = True)

        self.root_dir            = os.path.abspath(root_dir)
        self.indexed_mountpoints = self._index_mounted()
        self.jpgs, self.nefs     = self._audit_drive()


    def _index_mounted(self):
        """ TODO Get list of drives (Linux / Windows) """
        disk_index = {}

        _devices = psutil.disk_partitions(all=True)
        for i, _device in enumerate(_devices):
            disk_index[i] = Disk(_device)

        return disk_index

    def _audit_drive(self):
        """ Collect and return all JPG and NEF file paths from root_dir """
        jpg_pat = re.compile(".*\.JPE?G", flags=re.IGNORECASE)
        nef_pat = re.compile(".*\.NEF", flags=re.IGNORECASE)
        xmp_pat = re.compile(".*\.XMP", flags=re.IGNORECASE)
        jpgs    = []
        nefs    = []
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:

                file_path = os.path.join(root, file)

                if   jpg_pat.match(file):
                    jpgs.append(file_path)

                elif nef_pat.match(file):
                    nefs.append(file_path)

                elif xmp_pat.match(file):  # Ignore XMP files without warning
                    pass

                # Something that isn't a JPG, NEF, or XMP file - sounds the alarm!
                else:
                    print(f"Unknown file type: '{file_path}' - ignoring ...")

        return jpgs, nefs

    def _strip_file_path(self, fp):
        """ Return given file path (:fp:), without path, file extension,
        or format prefix

        XXX Perhaps stripping format prefix (`DSC_') is not necessary -
        will have to look at the data some more.

        """
        return fp.split(os.sep)[-1].split('.')[0].strip("DSC_")

    def pair_photos(self, reverse=False):
        """ Pair JPG and NEF files, returning paths to both files,
        if :reverse: specified return all JPG files without a match instead """
        matching_pairs = []

        # Collect of stripped file names, and associated paths, and build
        # dict out of them in the fmt:
        #   "stripped_file_name":"file_path"
        #
        tmp_nefs = [(self._strip_file_path(n),n) for n in self.nefs]
        tmp_nefs = { key: val for (key, val) in tmp_nefs }

        for jpg in self.jpgs:

            # Strip away path, file extension, format prefix
            jpg_file_name = jpg.split(os.sep)[-1].split('.')[0].strip("DSC_")

            pair = tmp_nefs.get(jpg_file_name)

            # Default behaviour: collect jpg:nef pairs
            if pair and not reverse:
                matching_pairs.append((jpg, pair))

            # Just collect unmatched JPG files
            elif not pair and reverse:
                matching_pairs.append(jpg)

        return matching_pairs


class Report():
    def __init__(self, write_path):
        """ XXX Just a holder class for various stats, lists
        which we want to write out to a report """

        self.write_path = write_path

        # Init beginning of new entry in report file
        self.write_line("*** NEW REPORT (" + time.strftime("%d/%m/%Y %H:%M:%S") + ") ***",
                        verbose=0)

    def write_line(self, s, verbose=1):
        """ Write out (append) given str to own report path,
        by default also prints to console what we are writing """

        if verbose > 0:
            print(s)

        if not s.endswith('\n'):
            s += '\n'

        with open(self.write_path, 'a') as f:
            f.write(s)

class Disk():
    def __init__(self, raw_device):
        """ TODO Build simple obj from :raw_device: obj """
        #print(f"Disk::__init__(self, {type(raw_device)} {raw_device})")
        for key in raw_device._fields:
            setattr(self, key, getattr(raw_device, key))

if __name__ == "__main__": main()
