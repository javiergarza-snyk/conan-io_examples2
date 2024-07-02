from init_project import DEVELOP, PACKAGES, PRODUCTS
from init_project import init_project, run, clean, add_repo, title, chdir


def replace(filepath, old, new):
    content = open(filepath).read()
    new_content = content.replace(old, new)
    if new_content == content:
        raise Exception("No replacement of '{}' happened".format(old))
    open(filepath, "w").write(new_content)


init_graph = False
package_single = False
package_multi = False
package_multi_lock = False


print("Checking current home")
out = run("conan config home")
print("Current home is:", out)
run("conan profile detect -f")

if init_graph:
    init_project()


############### Package pipeline ###################################
# Simulates a change done by one developer to ai.cpp code (a patch/bug fix)
# We do a change in one of the packages in the middle of 
# the graph, bump its version to 1.0.1 and create it

title("Package pipeline", c="*")
print("Doing changes to AI and bumping it to ai/1.0.1 version")
run("git checkout -- ai") # In case ai had previous changes 
replace("ai/src/ai.cpp", "Some Artificial", "SUPER BETTER Artificial")
replace("ai/include/ai.h", "intelligence=0", "intelligence=50")
replace("ai/conanfile.py", 'version = "1.0"', 'version = "1.1.0"')


############### Package pipeline: Single configuration ###################################
if package_single:
    title("Package pipeline, single configuration ")
    clean()
    add_repo(DEVELOP)
    out = run("conan create ai --build=missing:ai/*")
    assert "ai/1.1.0: SUPER BETTER Artificial Intelligence for aliens (Release)!" in out
    assert "ai/1.1.0: Intelligence level=50" in out
    # We don't want to disrupt developers or CI
    add_repo(PRODUCTS)
    run(f"conan upload ai* -r={PRODUCTS} -c")


############### Package pipeline: Multi configuration Release/Debug ###################################
if package_multi:
    title("Package pipeline, multi configuration")
    clean()
    add_repo(DEVELOP)
    # it could be distributed
    with chdir("ai"):
        run("conan create . --build=missing:ai/* -s build_type=Release --format=json", file_stdout="graph.json")
        run("conan list --graph=graph.json --graph-binaries=build --format=json", file_stdout="upload_release.json")
        add_repo(PACKAGES)
        run(f"conan upload -l=upload_release.json -r={PACKAGES} -c --format=json", file_stdout="upload_release.json")
        #clean()
        #add_repo(DEVELOP)
        run("conan create . --build=missing:ai/* -s build_type=Debug --format=json", file_stdout="graph.json")
        run("conan list --graph=graph.json --graph-binaries=build --format=json", file_stdout="upload_debug.json")
        # add_repo(PACKAGES)
        run(f"conan upload -l=upload_debug.json -r={PACKAGES} -c --format=json", file_stdout="upload_debug.json")

        print("- Running a promotion -")
        # aggregate the package list
        run("conan pkglist merge -l upload_release.json -l upload_debug.json --format=json", file_stdout="promote.json")
        clean()
        # We don't want to disrupt developers or CI
        add_repo(PACKAGES)
        add_repo(PRODUCTS)
        # Promotion with Artifactory CE (slow, can be improved with art:promote --artifactory-ce)
        out = run(f"conan download --list=promote.json -r={PACKAGES} --format=json", file_stdout="promote.json")
        out = run(f"conan upload --list=promote.json -r={PRODUCTS} -c")
        print(out)


############### Package pipeline: Multi configuration Release/Debug ###################################
if package_multi_lock:
    title("Package pipeline, multi configuration with Lockfiles")
    clean()
    with chdir("ai"):
        add_repo(DEVELOP)
        # it could be distributed
        run("conan lock create . --lockfile-out=conan.lock")
        run("conan lock create . -s build_type=Debug --lockfile=conan.lock --lockfile-out=conan.lock")  # To make sure we cover all

        clean()
        add_repo(DEVELOP)
        run("conan create . --build=missing:ai/* -s build_type=Release --lockfile=conan.lock --format=json", file_stdout="graph.json")
        run("conan list --graph=graph.json --graph-binaries=build --format=json", file_stdout="upload_release.json")
        add_repo(PACKAGES)
        run(f"conan upload -l=upload_release.json -r={PACKAGES} -c --format=json", file_stdout="upload_release.json")

        out = run("conan create . --build=missing:ai/* -s build_type=Debug --lockfile=conan.lock --format=json", file_stdout="graph.json")
        run("conan list --graph=graph.json --graph-binaries=build --format=json", file_stdout="upload_debug.json")
        run(f"conan upload -l=upload_debug.json -r={PACKAGES} -c --format=json", file_stdout="upload_debug.json")

        print("- Running a promotion -")
        # aggregate the package list
        run("conan pkglist merge -l upload_release.json -l upload_debug.json --format=json", file_stdout="promote.json")
        clean()
        # We don't want to disrupt developers or CI
        add_repo(PACKAGES)
        add_repo(PRODUCTS)
        # Promotion with Artifactory CE (slow, can be improved with art:promote --artifactory-ce)
        out = run(f"conan download --list=promote.json -r={PACKAGES} --format=json", file_stdout="promote.json")
        out = run(f"conan upload --list=promote.json -r={PRODUCTS} -c")
        print(out)


title("Product pipeline", c="*")

# Try to see if our main products keep working fine with that change ai/1.0.1
# lets build the consumers game and mapviewer applications
# to integrate the ai/1.0.1 changes
title("Lets see if this change ai/1.1.0 integrates correctly downstream")
clean()
add_repo(PRODUCTS)
add_repo(DEVELOP)
out = run("conan install --requires=mapviewer/1.0")
out = run("mapviewer", env_script="conanrun")
assert "mapviewer/1.0:serving the game (Release)!" in out

out = run("conan install --requires=game/1.0", error=True)
assert "ERROR: Missing prebuilt package for 'game/1.0'" in out
out = run("conan install --requires=game/1.0 --build=missing")
print(out)
out = run("game", env_script="conanrun")
assert "game/1.0:fun game (Release)!" in out
assert "ai/1.1.0: SUPER BETTER Artificial Intelligence for aliens (Release)!" in out
assert "ai/1.1.0: Intelligence level=50" in out
print(out)


exit()
############### Part 4 ###################################
# If we are building different configurations, like Release
# and Debug, something could change in between in deps.
# Lets introduce a lockfile to avoid this
print("- Part 4: Start using lockfiles -")
run("conan lock create --requires=game/1.0 --lockfile-out=game.lock")
# This change and ai/1.0.2 will not be used, it is after the lock
replace("ai/src/ai.cpp", "SUPER BETTER Artificial", "AUTONOMOUSLY EVOLVED Artificial")
out = run("conan create ai --version=1.0.2")
assert "ai/1.0.2: AUTONOMOUSLY EVOLVED Artificial Intelligence for aliens (Release)!" in out
# applying the lock, still ai/1.0.1 used
out = run("conan install --requires=game/1.0 --build=missing --lockfile=game.lock")
assert "ai/1.0.1" in out
assert "ai/1.0.2" not in out
out = run("game", env_script="conanrun")
assert "ai/1.0.1: SUPER BETTER Artificial Intelligence for aliens (Release)!" in out


############### Part 5 ###################################
# What happens if the change is done in the public headers?
# the minor version should be bumped, and that implies building
# the intermediate dependencies too. Lets start doing the change
print("- Part 5: Change a public header, bump minor version -")
replace("ai/include/ai.h", "intelligence=0", "intelligence=50")
out = run("conan create ai --version=1.1.0")
assert "ai/1.1.0: AUTONOMOUSLY EVOLVED Artificial Intelligence for aliens (Release)!" in out
assert "ai/1.1.0: Intelligence level=50" in out

############### Part 6 ###################################
# Lets see how the change in ai/1.1.0 requires building engine/1.0 too
# as the change is in the public api and engine->ai
print("- Part 6: Lets see if the minor 1.1.0 integrate downstream -")
run("conan install --requires=mapviewer/1.0")  # no changes, all good and ready
out = run("conan install --requires=game/1.0", error=True)
assert "ERROR: Missing prebuilt package for 'game/1.0'" in out
out = run("conan install --requires=game/1.0 --build=game/1.0", error=True)
assert "ERROR: Missing prebuilt package for 'engine/1.0'" in out

############### Part 7 ###################################
# Now that there are some cases that all the intermediate dependencies
# need to be built, we might want to distribute the build in a CI farm
# and for that we need to know what to build, and very importantly in what order
print("- Part 7: Compute the build-order -")
run("conan lock create --requires=game/1.0 --lockfile-out=game.lock")
out = run("conan lock create --requires=game/1.0 -s build_type=Debug --lockfile=game.lock --lockfile-out=game.lock")
assert "ai/1.1.0" in out
run("conan lock create --requires=mapviewer/1.0 --lockfile=game.lock --lockfile-out=game.lock")
out = run("conan lock create --requires=mapviewer/1.0 -s build_type=Debug --lockfile=game.lock --lockfile-out=game.lock")
lock = open("game.lock").read()
print(lock)

out = run("conan graph build-order --requires=game/1.0 --lockfile=game.lock --build=missing --order-by=recipe --format=json", file_stdout="game_bo.json")
out = run("conan graph build-order --requires=game/1.0 --lockfile=game.lock --build=missing -s build_type=Debug --order-by=recipe --format=json", file_stdout="game_bo_debug.json")
out = run("conan graph build-order --requires=mapviewer/1.0 --lockfile=game.lock --build=missing --order-by=recipe --format=json", file_stdout="mapviewer_bo.json")
out = run("conan graph build-order --requires=mapviewer/1.0 --lockfile=game.lock --build=missing -s build_type=Debug --order-by=recipe --format=json", file_stdout="mapviewer_bo_debug.json")

############### Part 8 ###################################
# If we have the build order for several applications, and 
# serveral configurations, there might be overlap. The build-orders
# can be merged in a single one, to optimize the building
print("- Part 8: Aggregate build orders -")
out = run("conan graph build-order-merge --file=game_bo.json --file=game_bo_debug.json "
          "--format=json", file_stdout="bo.json")


############### Part 9 ###################################
# Now that we have the aggregated build-order, lets execute it
# simulating a distributed build
print("- Part 9: Iterate the build-order -")
json_file = open("bo.json").read()
print(json_file)
to_build = json.loads(json_file)
to_build = to_build["order"]

for level in to_build:
    for elem in level:  # This can be executed in parallel
        ref = elem["ref"]
        # For every ref, multiple binary packages are being built. This can be done in parallel too
        # And often, for different OSs, they will need to be distributed to different build agents
        for packages in elem["packages"]:
            for package in packages:
                binary = package["binary"]
                if binary != "Build":
                    continue
                # TODO: The options are not used, they should be passed too
                filenames = package["filenames"]
                # This is the mapping between the build-order filenames and the profiles
                build_type = "Debug" if "debug" in filenames[0] else "Release"
                cmd = "conan install --requires={ref} --build={ref} --lockfile=game.lock -s build_type={bt}".format(ref=ref, bt=build_type)
                run(cmd)

out = run("game", env_script="conanrunenv-release-x86_64")
print(out)
assert "ai/1.1.0: AUTONOMOUSLY EVOLVED Artificial Intelligence for aliens (Release)!" in out
assert "ai/1.1.0: Intelligence level=50" in out
out = run("game", env_script="conanrunenv-debug-x86_64")
print(out)
assert "ai/1.1.0: AUTONOMOUSLY EVOLVED Artificial Intelligence for aliens (Debug)!" in out
assert "ai/1.1.0: Intelligence level=50" in out
