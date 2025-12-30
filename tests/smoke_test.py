import os
import sys
import subprocess
import glob
import venv
import shutil
import tempfile
import pytest

DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dist')

def run_in_venv(venv_path, cmd, cwd=None):
    """Run a command inside the venv."""
    if sys.platform == 'win32':
        python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
        bin_dir = os.path.join(venv_path, 'Scripts')
    else:
        python_exe = os.path.join(venv_path, 'bin', 'python')
        bin_dir = os.path.join(venv_path, 'bin')
    
    final_cmd = []
    if cmd[0] == 'python':
        final_cmd = [python_exe] + cmd[1:]
    elif cmd[0] == 'pip':
        final_cmd = [python_exe, '-m', 'pip'] + cmd[1:]
    elif cmd[0] == 'lmstxt':
        # Binaries are in bin/ or Scripts/
        if sys.platform == 'win32':
            bin_path = os.path.join(bin_dir, 'lmstxt.exe')
        else:
            bin_path = os.path.join(bin_dir, 'lmstxt')
        final_cmd = [bin_path] + cmd[1:]
    else:
        # Fallback or direct path
        final_cmd = cmd 
        
    print(f"Executing: {' '.join(final_cmd)}")
    subprocess.check_call(final_cmd, cwd=cwd)

@pytest.fixture
def temp_venv():
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = os.path.join(tmpdir, 'venv')
        venv.create(venv_path, with_pip=True)
        yield venv_path

def test_wheel_install(temp_venv):
    wheels = glob.glob(os.path.join(DIST_DIR, '*.whl'))
    if not wheels:
        pytest.skip("No wheels found in dist/")
    wheel = wheels[0]
    
    print(f"Testing wheel: {wheel}")
    run_in_venv(temp_venv, ['pip', 'install', wheel])
    run_in_venv(temp_venv, ['lmstxt', '--help'])

def test_sdist_install(temp_venv):
    sdists = glob.glob(os.path.join(DIST_DIR, '*.tar.gz'))
    if not sdists:
        pytest.skip("No sdists found in dist/")
    sdist = sdists[0]
    
    print(f"Testing sdist: {sdist}")
    run_in_venv(temp_venv, ['pip', 'install', sdist])
    run_in_venv(temp_venv, ['lmstxt', '--help'])

if __name__ == '__main__':
    # Manual execution block
    try:
        # Check Wheel
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = os.path.join(tmpdir, 'venv')
            print(f"Creating venv for wheel test in {venv_path}...")
            venv.create(venv_path, with_pip=True)
            
            wheels = glob.glob(os.path.join(DIST_DIR, '*.whl'))
            if wheels:
                print(f"Installing wheel {wheels[0]}...")
                run_in_venv(venv_path, ['pip', 'install', wheels[0]])
                print("Running lmstxt --help...")
                run_in_venv(venv_path, ['lmstxt', '--help'])
                print("Wheel test passed.")
            else:
                print("No wheels found.")
        
        # Check Sdist
        with tempfile.TemporaryDirectory() as tmpdir2:
            venv_path2 = os.path.join(tmpdir2, 'venv')
            print(f"Creating venv for sdist test in {venv_path2}...")
            venv.create(venv_path2, with_pip=True)
            
            sdists = glob.glob(os.path.join(DIST_DIR, '*.tar.gz'))
            if sdists:
                 print(f"Installing sdist {sdists[0]}...")
                 run_in_venv(venv_path2, ['pip', 'install', sdists[0]])
                 print("Running lmstxt --help...")
                 run_in_venv(venv_path2, ['lmstxt', '--help'])
                 print("Sdist test passed.")
            else:
                 print("No sdists found.")
                 
    except Exception as e:
        print(f"Smoke test failed: {e}")
        sys.exit(1)
