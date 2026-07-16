"""Fix [Content_Types].xml in pptx templates: image/.jpg -> image/jpeg"""
import zipfile
import shutil
import os
import glob
import tempfile

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "ppt_engine", "templates")
BAD_PATTERN = 'ContentType="image/.jpg"'
FIXED_VALUE = 'ContentType="image/jpeg"'

def fix_pptx(filepath):
    """Fix the [Content_Types].xml inside a pptx (zip) file."""
    # Read all entries
    z_read = zipfile.ZipFile(filepath, 'r')
    names = z_read.namelist()
    
    # Check if this file actually has the problem
    ct_content = z_read.read('[Content_Types].xml').decode('utf-8')
    if BAD_PATTERN not in ct_content:
        z_read.close()
        return False, "no issue"
    
    fixed_ct = ct_content.replace(BAD_PATTERN, FIXED_VALUE)
    
    # Write to a temp file, then replace original
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pptx', dir=os.path.dirname(filepath))
    os.close(tmp_fd)
    
    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as z_write:
        for item in z_read.infolist():
            data = z_read.read(item.filename)
            if item.filename == '[Content_Types].xml':
                data = fixed_ct.encode('utf-8')
            z_write.writestr(item, data)
    z_read.close()
    
    # Replace original with fixed version
    shutil.move(tmp_path, filepath)
    return True, "fixed"

def main():
    # Find all pptx files
    pptx_files = glob.glob(os.path.join(TEMPLATES_DIR, '**', '*.pptx'), recursive=True)
    
    bad_files = []
    for f in pptx_files:
        try:
            z = zipfile.ZipFile(f, 'r')
            ct = z.read('[Content_Types].xml').decode('utf-8')
            z.close()
            if BAD_PATTERN in ct:
                bad_files.append(f)
        except Exception as e:
            print(f"  ERROR reading {os.path.basename(f)}: {e}")
    
    print(f"Found {len(bad_files)} files with the issue:")
    for f in bad_files:
        print(f"  - {os.path.relpath(f, os.path.dirname(TEMPLATES_DIR))}")
    print()
    
    # Backup and fix each
    backup_dir = os.path.join(os.path.dirname(__file__), "template_bak")
    os.makedirs(backup_dir, exist_ok=True)
    
    fixed_count = 0
    for f in bad_files:
        basename = os.path.basename(f)
        rel_path = os.path.relpath(f, TEMPLATES_DIR)
        # Preserve subdirectory structure in backup
        backup_path = os.path.join(backup_dir, rel_path)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Backup
        shutil.copy2(f, backup_path)
        print(f"  Backup: {rel_path} -> template_bak/{rel_path}")
        
        # Fix
        ok, msg = fix_pptx(f)
        if ok:
            fixed_count += 1
            print(f"  FIXED:  {rel_path}")
        else:
            print(f"  SKIP:   {rel_path} ({msg})")
        print()
    
    print(f"Done. Backed up {len(bad_files)} files, fixed {fixed_count} files.")
    
    # Verify
    print("\n--- Verification ---")
    all_ok = True
    for f in pptx_files:
        try:
            z = zipfile.ZipFile(f, 'r')
            ct = z.read('[Content_Types].xml').decode('utf-8')
            z.close()
            if 'image/.jpg' in ct:
                print(f"  STILL BAD: {os.path.relpath(f, os.path.dirname(TEMPLATES_DIR))}")
                all_ok = False
        except:
            pass
    if all_ok:
        print("  All templates OK - no image/.jpg found in any template.")
    
if __name__ == '__main__':
    main()
