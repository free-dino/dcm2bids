import sys
import os
import subprocess
from pathlib import Path
import shutil
import pandas as pd
import tempfile
from dcm2bids import dcm2bids_gen

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path )

def find_excel_file(input_dir: Path) -> Path:
    excel_files = list(input_dir.glob("*.[xX][lL][sS][xX]")) + list(input_dir.glob("*.[xX][lL][sS]"))
    
    if not excel_files:
        print(f"ERROR: No Excel file found in {input_dir}")
        sys.exit(1)
    if len(excel_files) > 1:
        print(f"ERROR: Multiple Excel files found in {input_dir}:")
        for f in excel_files:
            print(f"  - {f.name}")
        sys.exit(1)
    
    return excel_files[0]

def excel_to_temp_csv(excel_file: Path) -> Path:
    temp_dir = Path(tempfile.gettempdir())
    temp_csv = temp_dir / "patient_mapping.csv"
    
    try:
        df = pd.read_excel(excel_file, engine="openpyxl")
        if df.shape[1] < 2:
            print("ERROR: Excel must have ≥2 columns (patient_folder, id)")
            sys.exit(1)
        
        df.iloc[:, :2].to_csv(temp_csv, index=False, header=["patient_folder", "id"])
        print(f"Converted {excel_file.name} → {temp_csv}")
        return temp_csv
    except Exception as e:
        print(f"ERROR: Failed to process Excel file: {str(e)}")
        sys.exit(1)

def process_patient_mapping(csv_file: Path, bids_output: Path) -> None:
    config = resource_path("dcm2bids.json")
    
    for _, row in pd.read_csv(csv_file).iterrows():
        patient_folder = Path(row["patient_folder"])
        subject_id = str(row["id"]).strip()
        
        if not patient_folder.exists():
            print(f"WARNING: Skipping missing folder '{patient_folder}'")
            continue
        
        print(f"Processing: {patient_folder.name} ---> sub-{subject_id}")
        app = dcm2bids_gen.Dcm2BidsGen(
            dicom_dir=[str(patient_folder)],
            participant=subject_id,
            config=str(config),
            output_dir=str(bids_output),
            session="",
            clobber=True,
            force_dcm2bids=True,
            bids_validate=False,
            log_level="INFO",
        )
        app.run()

def run_excel_dir(input_dir: str, bids_output: str) -> None:
    input_dir = Path(input_dir).resolve()
    bids_output = Path(bids_output).resolve()
    
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)
    
    # --- Excel Processing ---
    excel_file = find_excel_file(input_dir)
    print(f"Using Excel file: {excel_file.name}")
    
    temp_csv = excel_to_temp_csv(excel_file)
    
    bids_output.mkdir(parents=True, exist_ok=True)
    if not any(bids_output.iterdir()):
        print("Creating BIDS scaffold...")
        subprocess.run(["dcm2bids_scaffold", "-o", str(bids_output)], check=True)
    
    process_patient_mapping(temp_csv, bids_output)
    
    try:
        temp_csv.unlink()
    except OSError as e:
        print(f"WARNING: Could not delete temp file: {str(e)}")
    
    print("Script completed successfully")