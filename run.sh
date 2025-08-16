#!/usr/bin/env bash
set -euo pipefail

# --- User Input from CLI arguments ---
SOURCE_DICOM="${1:-}"
BIDS_OUTPUT="${2:-}"
CONFIG="${3:-dcm2bids.json}"

usage() { echo "Usage: $0 <SOURCE_DICOM> <BIDS_OUTPUT> [CONFIG_JSON]"; exit 1; }
[[ -z "$SOURCE_DICOM" || -z "$BIDS_OUTPUT" ]] && usage

# --- Required tools ---
for bin in dcm2bids_scaffold dcm2bids rsync; do
  command -v "$bin" >/dev/null 2>&1 || { echo "ERROR: '$bin' not found in PATH"; exit 1; }
done

# --- Set Paths Based on User Input ---
mkdir -p "$BIDS_OUTPUT"
DATASOURCE="$BIDS_OUTPUT/sourcedata"

# --- Pre-processing Checks ---
if [ -z "$(ls -A "$BIDS_OUTPUT")" ]; then
  echo "BIDS output directory '$BIDS_OUTPUT' is empty. Running dcm2bids_scaffold..."
  dcm2bids_scaffold -o "$BIDS_OUTPUT"
else
  echo "BIDS output directory '$BIDS_OUTPUT' is not empty. Skipping dcm2bids_scaffold."
fi

mkdir -p "$DATASOURCE"

# --- Sync source DICOMs into sourcedata ---
echo "Copying DICOM data from '$SOURCE_DICOM' into '$DATASOURCE'..."
rsync -a --progress "$SOURCE_DICOM"/ "$DATASOURCE"/

# --- Helper: detect whether a directory contains any DICOMs (recursively) ---
contains_dicoms() {
  local dir="$1"
  [[ -f "$dir/DICOMDIR" ]] && return 0
  find "$dir" -type f -iregex '.*\.\(dcm\|ima\)$' -print -quit | grep -q .
}

# --- Build the list of patient roots ---
PATIENT_DIRS=()

# Prefer immediate subdirs of sourcedata that contain DICOMs
while IFS= read -r -d '' d; do
  if contains_dicoms "$d"; then
    PATIENT_DIRS+=("$d")
  fi
done < <(find "$DATASOURCE" -mindepth 1 -maxdepth 1 -type d -print0)

# If none of the immediate subdirs had DICOMs, maybe sourcedata itself is a single "patient"
if ((${#PATIENT_DIRS[@]} == 0)) && contains_dicoms "$DATASOURCE"; then
  PATIENT_DIRS+=("$DATASOURCE")
fi

if ((${#PATIENT_DIRS[@]} == 0)); then
  echo "ERROR: No DICOM files found under '$DATASOURCE'."
  exit 1
fi

# --- Main Processing: run dcm2bids per patient root (recurses into all series) ---
SUBJECT_NUM=1
for PATIENT_DIR in "${PATIENT_DIRS[@]}"; do
  SUBJECT_ID=$(printf "%02d" "$SUBJECT_NUM")
  echo "Processing: $(basename "$PATIENT_DIR") → sub-$SUBJECT_ID"

  dcm2bids \
    -d "$PATIENT_DIR" \
    -p "$SUBJECT_ID" \
    -c "$CONFIG" \
    -o "$BIDS_OUTPUT" \
    --force

  ((SUBJECT_NUM++))
done

echo "Script finished successfully."
