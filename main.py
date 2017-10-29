import os
import sys
import time

def main():

    # XXX Just testing for now
    dir_name = "DEMO"
    print(f"Creating dir {os.path.curdir}{os.path.sep}{dir_name}")
    os.makedirs("DEMO")
    time.sleep(5)

if __name__ == "__main__": main()
