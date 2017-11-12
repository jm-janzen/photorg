import os
import re
import sys
import time
import psutil  # TODO Install automatically, if not already present?
import shutil

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
    input_disk_idx = prompt(msg="Select (from above numbers) which drive to write paired images to",
                                opts = "0 to "+str(drive_list_cnt))

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

    #
    # Step 2.
    #   Reports on photo pairs found in given directory, and copy to given write path
    #


    # Path for report file
    # TODO Use this
    report_path = os.path.join(write_dir, "REPORT.log")

    print(f"Will write paired files to {write_dir}")

    # Match up JPG:NEF files
    photo_pairs = pd.pair_photos()

    print(f"Pairs found: {photo_pairs}")

    # Create output dir if it doesn't already exist
    if not os.path.isdir(write_dir):
        os.makedirs(write_dir)

    #
    # XXX Investigate: Is meta-data lost in copy operation ?
    #
    for jpg, nef in photo_pairs:
        print(f"cp {jpg} {write_dir}")
        shutil.copy(jpg, write_dir)
        print(f"cp {nef} {write_dir}")
        shutil.copy(nef, write_dir)

    #
    # TODO Write report containing:
    #   JPG:NEF pairs copied
    #   JPG files with no matching NEFs (important!)
    #   NEF files with no JPGs (less important)
    #   Any issues along the way
    #


    # All done - notify and exit
    prompt(msg="Done.", opts="Enter to exit")

def prompt(msg, opts, exit_after=False):
    """ Print :msg: and input :opts: to terminal, and optionally :after_after: user input received """
    user_input = input(f"{str(msg)} [{str(opts)} (q to quit)] >>> ")

    # Quit if specified in invocation, or user input
    if user_input.lower() == 'q' or exit_after:
        exit(1)

    return user_input

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
        jpgs    = []
        nefs    = []
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:

                file_path = os.path.join(root, file)

                if   jpg_pat.match(file):
                    jpgs.append(file_path)

                elif nef_pat.match(file):
                    nefs.append(file_path)

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

    def pair_photos(self):
        """ Pair JPG and NEF files, returning paths to both files """
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
            if pair:
                matching_pairs.append((jpg, pair))

        return matching_pairs

class Disk():
    def __init__(self, raw_device):
        """ TODO Build simple obj from :raw_device: obj """
        #print(f"Disk::__init__(self, {type(raw_device)} {raw_device})")
        for key in raw_device._fields:
            setattr(self, key, getattr(raw_device, key))

if __name__ == "__main__": main()
