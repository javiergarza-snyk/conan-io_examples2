import os
import subprocess

def run(cmd, error=False):
    # Used by tools/scm check_repo only (see if repo ok with status)
    print("Running: {}".format(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    out = out.decode("utf-8")
    err = err.decode("utf-8")
    ret = process.returncode

    output = err + out
    if ret != 0 and not error:
        raise Exception("Failed cmd: {}\n{}".format(cmd, output))
    if ret == 0 and error:
        raise Exception("Cmd succeded (failure expected): {}\n{}".format(cmd, output))
    return output


# Part 1: Setup the project initial state
run('conan remove "*" -f')  # Make sure no packages from last run
run("conan create matrix --version=1.0")
run("conan create ai --version=1.0")
run("conan create physx --version=1.0")
run("conan create engine --version=1.0")
out = run("conan create game --version=1.0")
print(out)
out = run("conan create gameserver --version=1.0")
print(out)
"""
out = run("conan install game", error=True)
assert "ERROR: Version conflict: engine/1.0->math/1.0, game/1.0->math/2.0" in out

# Add the requires "force=True" fixes it
content = open("game/conanfile.py").read()
new_content = content.replace('self.requires("math/2.0")',
                              'self.requires("math/2.0", force=True)')
open("game/conanfile.py", "w").write(new_content)
# The jump in major version requires building  a new engine/1.0 binary
out = run("conan install game", error=True)   # binary missing
assert "ERROR: Missing binary: engine/1.0" in out

# With force=True and --build=missing, it works
run("conan install game --build=missing")

# restore the original contents:
open("game/conanfile.py", "w").write(content)
"""