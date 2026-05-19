import os
import difflib

dir_a = r"d:\AMS"
dir_b = r"d:\AMS\scratch\replit_repo"

ignore_dirs = {'.git', '.github', 'venv', 'scratch', '.local', '.agents', '__pycache__', 'media', 'static_files', 'staticfiles'}
ignore_files = {'.env', 'db.sqlite3', 'db_check.txt', 'env.txt', 'AMS.png', 'AMS_PS.png', 'Facilitation Technics.docx', 'Facilitation Technics.pdf', 'Session Plan Template Practical.pdf', 'Session plan template Delivering.pdf', 'Prompt.docx'}

def get_files_dict(base_dir):
    files_dict = {}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        for f in files:
            if f in ignore_files or f.endswith('.pyc') or f.endswith('.png') or f.endswith('.pdf') or f.endswith('.docx') or f.endswith('.sqlite3'):
                continue
            rel_path = os.path.relpath(os.path.join(root, f), base_dir)
            files_dict[rel_path] = os.path.join(root, f)
    return files_dict

files_a = get_files_dict(dir_a)
files_b = get_files_dict(dir_b)

all_rel_paths = sorted(list(set(files_a.keys()) | set(files_b.keys())))

only_in_a = []
only_in_b = []
modified = []
identical = []

for rel in all_rel_paths:
    in_a = rel in files_a
    in_b = rel in files_b
    if in_a and not in_b:
        only_in_a.append(rel)
    elif in_b and not in_a:
        only_in_b.append(rel)
    else:
        path_a = files_a[rel]
        path_b = files_b[rel]
        
        try:
            with open(path_a, 'r', encoding='utf-8', errors='ignore') as fa:
                lines_a = [line.rstrip() for line in fa.readlines()]
            with open(path_b, 'r', encoding='utf-8', errors='ignore') as fb:
                lines_b = [line.rstrip() for line in fb.readlines()]
            
            if lines_a == lines_b:
                identical.append(rel)
            else:
                modified.append(rel)
        except Exception as e:
            print(f"Error reading {rel}: {e}")
            modified.append(rel)

print("=== ONLY IN LOCAL DEVELOPMENT (d:\\AMS) ===")
for r in only_in_a:
    print(r)

print("\n=== ONLY IN REPLIT-AGENT BRANCH (scratch\\replit_repo) ===")
for r in only_in_b:
    print(r)

print("\n=== MODIFIED / DIFFERENT FILES ===")
for r in modified:
    print(r)

print(f"\nSummary: {len(only_in_a)} only in local, {len(only_in_b)} only in Replit, {len(modified)} modified, {len(identical)} identical.")
