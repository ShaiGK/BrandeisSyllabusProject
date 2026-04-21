"""
Converts syllabus .txt files into a JSON file that Label Studio can import.

Usage:
    python prepare_for_label_studio.py

Walks the syllabi/ folder tree, reads each .txt file, and outputs
label_studio_tasks.json. Run from the project root.
"""

import os
import json
import glob
import re


def parse_filepath(filepath):
    """Extract metadata from the folder structure and filename.

    Expected structure:
      syllabi/<semester>/<school>/<department>/<filename>.txt

    Filename format:
      243CHEM 15A 1 Honors General Chemistry I Thomas Pochapsky.txt
    """
    parts = filepath.replace('\\', '/').split('/')

    # Find where 'syllabi' is in the path
    try:
        idx = parts.index('syllabi')
    except ValueError:
        idx = 0

    remaining = parts[idx + 1:]  # everything after syllabi/

    semester = remaining[0] if len(remaining) > 0 else 'unknown'
    school = remaining[1] if len(remaining) > 1 else 'unknown'
    department = remaining[2] if len(remaining) > 2 else 'unknown'
    filename = remaining[3] if len(remaining) > 3 else remaining[-1]

    # Clean up semester — extract readable name
    # e.g. "Fall Semester 2024 (243)" -> "Fall 2024"
    sem_match = re.search(r'(Fall|Spring|Summer)\s*(?:Semester\s*)?(\d{4})', semester)
    semester_short = f"{sem_match.group(1)} {sem_match.group(2)}" if sem_match else semester

    # Extract course info from filename
    # e.g. "243CHEM 15A 1 Honors General Chemistry I Thomas Pochapsky.txt"
    course_name = os.path.splitext(filename)[0]

    return {
        'semester': semester,
        'semester_short': semester_short,
        'school': school,
        'department': department,
        'filename': filename,
        'course_name': course_name,
    }


def main():
    # Find all .txt files in syllabi/ subfolders
    txt_files = sorted(glob.glob('syllabi/**/*.txt', recursive=True))

    if not txt_files:
        print("ERROR: No .txt files found in syllabi/ folder.")
        print("Make sure you run this script from your project root folder")
        print("(the folder that contains the syllabi/ directory).")
        return

    tasks = []

    for filepath in txt_files:
        meta = parse_filepath(filepath)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read().strip()

        if not text:
            continue

        # Build a unique ID
        doc_id = os.path.splitext(meta['filename'])[0]

        # Metadata display string for annotators
        meta_display = (
            f"Semester: {meta['semester_short']}  |  "
            f"School: {meta['school']}  |  "
            f"Department: {meta['department']}  |  "
            f"Course: {meta['course_name']}"
        )

        task = {
            "data": {
                "doc_id": doc_id,
                "meta_display": meta_display,
                "text": text,
                "semester": meta['semester'],
                "school": meta['school'],
                "department": meta['department'],
                "course_name": meta['course_name'],
                "source_file": filepath,
            }
        }
        tasks.append(task)

    # Write output
    output_path = 'label_studio_tasks.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

    print(f"Done! Processed {len(tasks)} syllabi.")
    print(f"Output saved to: {output_path}")
    print(f"\nNext step: Run 'python annotate.py start' to begin annotating.")


if __name__ == '__main__':
    main()