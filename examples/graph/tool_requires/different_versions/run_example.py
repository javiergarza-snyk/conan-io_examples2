import os

from test.examples_tools import run, tmp_dir


run("conan create gcc --version=1.0")
run("conan create gcc --version=2.0")

output = run("conan create wine")
assert "MYGCC=1.0!!" in output
assert "MYGCC=2.0!!" in output
