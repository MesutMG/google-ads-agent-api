import os
import subprocess
from pathlib import Path

# Files/extensions to explicitly ignore to keep the dump clean
IGNORE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', 
    '.ttf', '.eot', '.zip', '.tar', '.gz', '.pdf', '.exe', '.lock'
}

OUTPUT_FILE = "FullText.txt"

def get_git_tracked_files(root_dir):
    """Uses git to get a list of all non-ignored files."""
    try:
        # Get all non-ignored files (tracked + untracked)
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
        result = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, check=True)
        files = result.stdout.splitlines()
        return [Path(f) for f in files]
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Git command failed or git not found. Reading all files manually...")
        return None

def is_text_file(filepath):
    """Check if a file is readable text (non-binary)."""
    if filepath.suffix.lower() in IGNORE_EXTENSIONS:
        return False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(1024)
        return True
    except (UnicodeDecodeError, PermissionError):
        return False

def dump_project_to_text(root_dir="."):
    root_path = Path(root_dir).resolve()
    output_path = root_path / OUTPUT_FILE

    # Get non-ignored files via git
    file_list = get_git_tracked_files(root_path)

    if file_list is None:
        # Fallback if git is not initialized: walk through files
        file_list = []
        for path in root_path.rglob('*'):
            if path.is_file() and not any(part.startswith('.') for part in path.parts):
                file_list.append(path.relative_to(root_path))

    count = 0
    with open(output_path, "w", encoding="utf-8") as outfile:
        for rel_path in file_list:
            full_path = root_path / rel_path

            # Skip the output file itself & binary files
            if full_path == output_path or not full_path.exists() or not is_text_file(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as infile:
                    content = infile.read()

                outfile.write(f"{rel_path}:\n")
                outfile.write(content)
                outfile.write("\n\n" + "=" * 80 + "\n\n")
                count += 1
                print(f"Added: {rel_path}")

            except Exception as e:
                print(f"Skipped {rel_path}: {e}")

    print(f"\nDone! Successfully dumped {count} files into '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    dump_project_to_text()