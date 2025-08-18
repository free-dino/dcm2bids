import subprocess
import os
import sys
from gooey import Gooey, GooeyParser
from run_raw import *
from run_excel import *
import shutil

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path )

def cleanup_tmp_dirs(output_dir):
    for item in os.listdir(output_dir):
        full_path = os.path.join(output_dir, item)
        if os.path.isdir(full_path) and item.startswith("tmp"):
            print(f"Deleting temporary folder: {full_path}")
            shutil.rmtree(full_path, ignore_errors=True)


@Gooey(
    program_name="DICOM to BIDS Converter",
    default_size=(800, 600),
    show_stop_button=False,
    layout='column',
    clear_before_run=True,
    image_dir=resource_path("assets/")
)
def main():
    parser = GooeyParser(description="Convert DICOM folder to BIDS format")

    # --- One Group: keeps order consistent ---
    group = parser.add_argument_group(
        "Settings",
        gooey_options={'columns': 1}
    )

    # First: directories
    group.add_argument(
        "source_dicom",
        metavar="Input Path",
        help="Select DICOM folder OR Excel file",
        widget="DirChooser",
        gooey_options={'order': 1}
    )
    group.add_argument(
        "bids_output",
        metavar="BIDS Output Folder",
        help="Select output directory for BIDS dataset",
        widget="DirChooser",
        gooey_options={'order': 2}
    )

    # Then: processing mode (radio buttons)
    mode = group.add_mutually_exclusive_group(
        required=True,
        gooey_options={'title': "Processing Mode", 'order': 3}
    )
    mode.add_argument(
        '--raw',
        action='store_true',
        help='Process raw DICOM folders',
        gooey_options={'radio': True, 'label': 'DICOM Folders to BIDS)'}
    )
    mode.add_argument(
        '--excel',
        action='store_true',
        help='Process using Excel mapping file',
        gooey_options={'radio': True, 'label': 'Excel to BIDS)'}
    )

    args = parser.parse_args()

    try:
        if args.raw:
            print("Running...")
            if not os.path.isdir(args.source_dicom):
                print("Error: This mode requires a directory DICOM folder, but you selected a file.")
                exit(1)
            run_dicom_to_bids(args.source_dicom, args.bids_output)
            cleanup_tmp_dirs(args.bids_output)

        elif args.excel:
            print("Running...")
            if not os.path.isdir(args.source_dicom):
                print("Error: Choose a directory")
                exit(1)
            run_excel_dir(args.source_dicom, args.bids_output)
            cleanup_tmp_dirs(args.bids_output)

    except subprocess.CalledProcessError as e:
        print(f"Script failed with exit code {e.returncode}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
