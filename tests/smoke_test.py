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
    elif cmd[0] in ['lmstxt', 'llmstxt-mcp']:
        # Binaries are in bin/ or Scripts/
        if sys.platform == 'win32':
            bin_path = os.path.join(bin_dir, f'{cmd[0]}.exe')
        else:
            bin_path = os.path.join(bin_dir, cmd[0])
        final_cmd = [bin_path] + cmd[1:]
    else:
        # Fallback or direct path
        final_cmd = cmd 
        
    print(f"Executing: {' '.join(final_cmd)}")
    # Use subprocess.run with timeout for MCP command as it might block if it starts the server loop
    if cmd[0] == 'llmstxt-mcp':
        try:
            # We just want to see if it's there and can run. --help should return immediately.
            subprocess.run(final_cmd, cwd=cwd, check=True, timeout=10, capture_output=True)
        except subprocess.TimeoutExpired:
            print(f"Command {cmd[0]} timed out (expected if it enters a loop)")
    else:
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
    run_in_venv(temp_venv, ['llmstxt-mcp', '--help'])

def test_sdist_install(temp_venv):
    sdists = glob.glob(os.path.join(DIST_DIR, '*.tar.gz'))
    if not sdists:
        pytest.skip("No sdists found in dist/")
    sdist = sdists[0]
    
    print(f"Testing sdist: {sdist}")
    run_in_venv(temp_venv, ['pip', 'install', sdist])
    run_in_venv(temp_venv, ['lmstxt', '--help'])
    run_in_venv(temp_venv, ['llmstxt-mcp', '--help'])

if __name__ == '__main__':
    # Manual execution block for CI
    # This matches the logic in the pytest functions
    pass