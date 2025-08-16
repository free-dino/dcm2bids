#!/bin/bash

# --- User Input from CLI arguments ---
INPUT_DIR="$1"
BIDS_OUTPUT="$2"

if [ -z "$INPUT_DIR" ] || [ -z "$BIDS_OUTPUT" ]; then
    echo "Usage: $0 <INPUT_DIR> <BIDS_OUTPUT>"
    echo "Note: INPUT_DIR must contain exactly one Excel file"
    exit 1
fi

# --- Check for required tools ---
REQUIRED_TOOLS=("dcm2bids_scaffold" "dcm2bids" "python3")
for tool in "${REQUIRED_TOOLS[@]}"; do
    which "$tool" >/dev/null || { echo "Error: $tool not found in PATH"; exit 1; }
done

# --- Set Paths ---
CONFIG="dcm2bids.json"
TEMP_CSV="/tmp/patient_mapping.csv"

# --- Find the Excel file ---
EXCEL_FILE=$(find "$INPUT_DIR" -maxdepth 1 -type f \( -iname "*.xlsx" -o -iname "*.xls" \))
if [ -z "$EXCEL_FILE" ]; then
    echo "Error: No Excel file found in $INPUT_DIR"
    exit 1
fi
if [ $(echo "$EXCEL_FILE" | wc -l) -ne 1 ]; then
    echo "Error: More than one Excel file found in $INPUT_DIR"
    exit 1
fi

echo "Using Excel file: $EXCEL_FILE"

# --- Convert Excel to CSV ---
echo "Converting Excel mapping to CSV..."
python3 -c "
import pandas as pd
import os
try:
    df = pd.read_excel('$EXCEL_FILE', engine='openpyxl')
    required_cols = df.columns[:2].tolist()
    if len(required_cols) < 2:
        print('Error: Excel file must have at least 2 columns: patient_folder, id')
        exit(1)
    df.iloc[:, :2].to_csv('$TEMP_CSV', index=False, header=['patient_folder','id'])
    print(f'Successfully converted {os.path.basename('$EXCEL_FILE')} to CSV')
except Exception as e:
    print(f'Error processing Excel file: {str(e)}')
    exit(1)
" || { echo "Excel conversion failed"; exit 1; }

# --- BIDS Setup ---
mkdir -p "$BIDS_OUTPUT"
if [ -z "$(ls -A "$BIDS_OUTPUT")" ]; then
    echo "Creating BIDS scaffold..."
    dcm2bids_scaffold -o "$BIDS_OUTPUT"
fi

# --- Main Processing ---
while IFS=, read -r patient_folder subject_id; do
    # Skip header
    [[ "$patient_folder" == "patient_folder" ]] && continue
    [[ -z "$patient_folder" || -z "$subject_id" ]] && continue

    if [ ! -d "$patient_folder" ]; then
        echo "Warning: Patient folder '$patient_folder' not found, skipping"
        continue
    fi

    echo "Processing: $patient_folder → sub-$subject_id"

    dcm2bids \
        -d "$patient_folder" \
        -p "$subject_id" \
        -c "$CONFIG" \
        -o "$BIDS_OUTPUT" \
        --force
done < "$TEMP_CSV"

# Cleanup
rm -f "$TEMP_CSV"
echo "Script completed successfully."
