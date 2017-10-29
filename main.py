import os
import sys
import time
import psutil

def main():

    # Validate and use passed argument as root operating drive
    pd = PhotoDrive(sys.argv)
    print(f"Using {pd.root_dir} as root directory")

    # Prompt for which drive to write to
    drive_list_str = ''
    for i, d in pd.indexed_mountpoints.items():
        drive_list_str += f"[{i}]\t{d.mountpoint}\n"

    input_disk_idx = prompt(msg="Select which drive to write paired images to:\n"+drive_list_str,
                            opts = "0 to "+str(drive_list_str.count('\n') - 1))

    write_path = os.path.join(pd.indexed_mountpoints.get(int(input_disk_idx)).mountpoint, "out")
    print(f"Will write paired files to {write_path}")

    # TODO Get unambiguous read/write root paths

    # TODO Find all dirs with JPG files only

    # TODO Find all dirs with NEF files only

def prompt(msg, opts, exit_after=False):
    """ Print :msg: and input :opts: to terminal, and optionally :after_after: user input received """
    user_input = input(f"{str(msg)} [{str(opts)}] >>> ")

    if exit_after: exit()

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


    def _index_mounted(self):
        """ TODO Get list of drives (Linux / Windows) """
        disk_index = {}

        _devices = psutil.disk_partitions(all=True)
        for i, _device in enumerate(_devices):
            disk_index[i] = Disk(_device)

        return disk_index

class Disk():
    def __init__(self, raw_device):
        """ TODO Build simple obj from :raw_device: obj """
        #print(f"Disk::__init__(self, {type(raw_device)} {raw_device})")
        for key in raw_device._fields:
            setattr(self, key, getattr(raw_device, key))

if __name__ == "__main__": main()
