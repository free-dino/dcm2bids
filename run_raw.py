import os
import shutil
import subprocess
import sys
from pathlib import Path
import sys

from dcm2bids import dcm2bids_gen

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path )

def contains_dicoms(directory: Path) -> bool:
    dicomdir = directory / "DICOMDIR"
    if dicomdir.is_file():
        return True

    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".dcm"):
                return True
    return False

def run_dicom_to_bids(source_dicom: str, bids_output: str, config: str = "dcm2bids.json"):
    source_dicom = Path(source_dicom).resolve()
    bids_output = Path(bids_output).resolve()
    datasource = bids_output / "sourcedata"

    if not source_dicom.exists():
        print(f"ERROR: Source path '{source_dicom}' not found")
        sys.exit(1)
        
    bids_output.mkdir(parents=True, exist_ok=True)
    datasource.mkdir(parents=True, exist_ok=True)

    if not any(bids_output.iterdir()):
        print(f"BIDS output '{bids_output}' is empty --> running dcm2bids_scaffold")
        subprocess.run(["dcm2bids_scaffold", "-o", str(bids_output)], check=True)
    else:
        print(f"BIDS output '{bids_output}' is not empty ---> skipping scaffold")

    print(f"Copying DICOM data from '{source_dicom}' ---> '{datasource}'")
    if source_dicom.is_dir():
        # sync all contents
        for item in source_dicom.iterdir():
            dest = datasource / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    else:
        print("ERROR: Source must be a directory containing DICOMs")
        sys.exit(1)

    patient_dirs = []
    for d in datasource.iterdir():
        if d.is_dir() and contains_dicoms(d):
            patient_dirs.append(d)

    if not patient_dirs and contains_dicoms(datasource):
        patient_dirs.append(datasource)

    if not patient_dirs:
        print(f"ERROR: No DICOM files found under '{datasource}'")
        sys.exit(1)

    for idx, patient_dir in enumerate(patient_dirs, start=1):
        subject_id = f"{idx:02d}"
        print(f"Processing: {patient_dir.name} → sub-{subject_id}")
        config_path = resource_path(config)
        app = dcm2bids_gen.Dcm2BidsGen(
            dicom_dir=[str(patient_dir)],
            participant=subject_id,
            config=str(config_path),
            output_dir=str(bids_output),
            session="",
            clobber=True,
            force_dcm2bids=True,
            bids_validate=False,
            log_level="INFO"
        )
        app.run()

    print("Script finished successfully.")
