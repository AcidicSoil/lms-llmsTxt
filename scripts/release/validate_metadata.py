#!/usr/bin/env python3
import sys
import argparse
import subprocess
import glob
import os
import zipfile
import tarfile
from email.parser import Parser

def run_twine_check(dist_files):
    """Run twine check on distribution files."""
    print("Running twine check...")
    try:
        # Try running twine as a command
        cmd = ["twine", "check"] + dist_files
        subprocess.check_call(cmd)
        print("Twine check passed.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            # Try running twine as a module
            cmd = [sys.executable, "-m", "twine", "check"] + dist_files
            subprocess.check_call(cmd)
            print("Twine check passed.")
        except subprocess.CalledProcessError:
            print("Twine check failed.")
            sys.exit(1)
        except Exception as e:
            print(f"Error running twine: {e}")
            print("Ensure 'twine' is installed (pip install twine).")
            sys.exit(1)

def check_direct_urls(dist_files):
    """Check for direct URL dependencies in metadata."""
    print("Checking for direct URL dependencies...")
    has_error = False
    
    for file_path in dist_files:
        metadata = None
        if file_path.endswith('.whl'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('METADATA'):
                        metadata = zf.read(name).decode('utf-8')
                        break
        elif file_path.endswith('.tar.gz'):
            with tarfile.open(file_path, 'r:gz') as tf:
                for member in tf.getmembers():
                    if member.name.endswith('PKG-INFO'):
                        f = tf.extractfile(member)
                        if f:
                            metadata = f.read().decode('utf-8')
                        break
        
        if not metadata:
            print(f"Warning: Could not find metadata in {file_path}")
            continue

        # Parse metadata
        parser = Parser()
        msg = parser.parsestr(metadata)
        requires_dist = msg.get_all('Requires-Dist') or []
        
        for req in requires_dist:
            # Check for direct URL references (PEP 440/508)
            # Typically "name @ url"
            if '@' in req and ('http' in req or 'git+' in req or 'file:' in req):
                 print(f"ERROR: Direct URL dependency found in {file_path}: {req}")
                 has_error = True
            # Also simple "git+" at start is legacy but should be caught
            elif req.strip().startswith('git+'):
                 print(f"ERROR: Direct URL dependency found in {file_path}: {req}")
                 has_error = True

    if has_error:
        print("Validation failed: Direct URL dependencies detected.")
        sys.exit(1)
    else:
        print("Dependency check passed: No direct URLs found.")

def main():
    parser = argparse.ArgumentParser(description="Validate distribution artifacts.")
    parser.add_argument('dist_dir', nargs='?', default='dist', help='Directory containing artifacts')
    args = parser.parse_args()
    
    if not os.path.exists(args.dist_dir):
        print(f"Directory not found: {args.dist_dir}")
        sys.exit(1)

    dist_files = glob.glob(os.path.join(args.dist_dir, '*'))
    dist_files = [f for f in dist_files if f.endswith('.whl') or f.endswith('.tar.gz')]
    
    if not dist_files:
        print(f"No artifacts found in {args.dist_dir}")
        sys.exit(1)
        
    run_twine_check(dist_files)
    check_direct_urls(dist_files)
    print("All validations passed.")

if __name__ == '__main__':
    main()
