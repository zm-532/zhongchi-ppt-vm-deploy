"""Fix WPS-created pptx templates by re-saving through WPS COM, making them PowerPoint-compatible."""
import win32com.client
import os
import glob
import time
import shutil
import tempfile
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "ppt_engine" / "templates"

def find_affected_templates():
    """Find all pptx templates that have ZIP directory entries (WPS-created, potentially broken)."""
    import zipfile
    pptx_files = glob.glob(str(TEMPLATES_DIR / "**" / "*.pptx"), recursive=True)
    affected = []
    for f in pptx_files:
        z = zipfile.ZipFile(f)
        has_dir_entries = any(n.endswith('/') for n in z.namelist())
        z.close()
        if has_dir_entries:
            affected.append(f)
    return affected

def wps_resave(filepath):
    """Open file with WPS COM and save to a temp file. Returns temp file path or None."""
    wps = None
    pres = None
    try:
        wps = win32com.client.DispatchEx("kwpp.Application")
        wps.DisplayAlerts = 0  # Suppress dialogs
        
        src = os.path.abspath(filepath)
        # Create temp file path
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pptx', dir=os.path.dirname(src))
        os.close(tmp_fd)
        os.remove(tmp_path)  # Remove it, WPS will create it
        
        pres = wps.Presentations.Open(src)
        slide_count = pres.Slides.Count
        pres.SaveAs(tmp_path)
        pres.Close()
        pres = None
        
        return tmp_path, slide_count
    except Exception as e:
        return None, str(e)
    finally:
        if pres:
            try: pres.Close()
            except: pass
        if wps:
            try: wps.Quit()
            except: pass
        time.sleep(1)  # Wait for WPS to fully exit

def test_powerpoint_open(filepath):
    """Test if PowerPoint COM can open the file. Returns (success, slide_count_or_error)."""
    pp = None
    pres = None
    try:
        pp = win32com.client.DispatchEx("PowerPoint.Application")
        pres = pp.Presentations.Open(os.path.abspath(filepath), WithWindow=False)
        count = pres.Slides.Count
        pres.Close()
        pres = None
        return True, count
    except Exception as e:
        return False, str(e)
    finally:
        if pres:
            try: pres.Close()
            except: pass
        if pp:
            try: pp.Quit()
            except: pass
        time.sleep(1)

def main():
    affected = find_affected_templates()
    print(f"Found {len(affected)} affected templates")
    
    # Backup directory already exists from previous fix (template_bak/)
    # We'll save WPS-repaired versions in place
    
    results = []
    for i, filepath in enumerate(affected):
        rel = os.path.relpath(filepath, TEMPLATES_DIR)
        print(f"\n[{i+1}/{len(affected)}] {rel}")
        
        # WPS re-save
        tmp_path, info = wps_resave(filepath)
        if tmp_path is None:
            print(f"  WPS re-save FAILED: {info}")
            results.append((filepath, "WPS_FAIL", info))
            continue
        
        wps_slides = info
        print(f"  WPS saved: {wps_slides} slides -> {os.path.basename(tmp_path)}")
        
        # Test with PowerPoint COM
        ok, pp_info = test_powerpoint_open(tmp_path)
        if ok:
            print(f"  PowerPoint COM: OK ({pp_info} slides)")
            
            # Verify slide count matches
            if pp_info == wps_slides:
                # Replace original with repaired version
                shutil.move(tmp_path, filepath)
                print(f"  REPLACED original with repaired version")
                results.append((filepath, "FIXED", f"{pp_info} slides"))
            else:
                print(f"  WARNING: slide count mismatch (WPS={wps_slides}, PP={pp_info})")
                # Still replace, but note the warning
                shutil.move(tmp_path, filepath)
                print(f"  REPLACED with warning")
                results.append((filepath, "FIXED_WITH_WARNING", f"WPS={wps_slides},PP={pp_info}"))
        else:
            print(f"  PowerPoint COM: FAIL: {pp_info}")
            # Don't replace, keep original
            os.remove(tmp_path)
            print(f"  KEPT original (repaired version still failed)")
            results.append((filepath, "STILL_BAD", pp_info))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    fixed = [r for r in results if r[1] in ("FIXED", "FIXED_WITH_WARNING")]
    failed = [r for r in results if r[1] in ("WPS_FAIL", "STILL_BAD")]
    print(f"Fixed: {len(fixed)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed templates:")
        for path, status, info in failed:
            print(f"  {os.path.relpath(path, TEMPLATES_DIR)}: {status} - {info}")

if __name__ == '__main__':
    main()
