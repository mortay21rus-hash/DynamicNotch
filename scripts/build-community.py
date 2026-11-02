#!/usr/bin/env python3
"""Build and package the arm64 community app without modifying the installed app."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/mortay21rus-hash/DynamicNotch"
TAG = "community-1.6.3-25.6.2"
BUILD = "25.6.2"


def run(arguments: list[str]) -> None:
    subprocess.run(arguments, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/community")
    parser.add_argument("--packages", type=Path, help="Optional existing Swift package checkout directory")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    derived = output / "DerivedData"
    packages = (args.packages or output / "SourcePackages").resolve()
    archive = output / "DynamicNotch-Community-arm64-25.6.2.zip"
    staging = output / "package"
    if staging.exists() or archive.exists():
        parser.error("Choose a fresh output directory; an existing package will not be overwritten.")

    # These flags also remap #filePath strings used by source-resource fallbacks.
    # subprocess arguments are passed directly: no shell or command substitution.
    mappings = [(ROOT, "/src"), (output, "/build"), (packages, "/packages"), (Path.home(), "/home/builder")]
    flags = ["$(inherited)"]
    for original, replacement in mappings:
        mapping = shlex.quote(f"{original}={replacement}")
        flags.extend(["-file-prefix-map", mapping, "-debug-prefix-map", mapping])
    command = [
        "xcodebuild", "-project", "DynamicNotch.xcodeproj", "-scheme", "DynamicNotch",
        "-configuration", "Release", "-destination", "platform=macOS,arch=arm64",
        "-derivedDataPath", str(derived), "-clonedSourcePackagesDirPath", str(packages),
        "-disableAutomaticPackageResolution", "CODE_SIGNING_ALLOWED=NO",
        "MACOSX_DEPLOYMENT_TARGET=26.0", f"CURRENT_PROJECT_VERSION={BUILD}",
        "OTHER_SWIFT_FLAGS=" + " ".join(flags), "build",
    ]
    log = output / "build.log"
    with log.open("w") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(f"Build failed. See {log}")

    built = derived / "Build/Products/Release/DynamicNotch.app"
    info = plistlib.loads((built / "Contents/Info.plist").read_bytes())
    if info.get("CFBundleVersion") != BUILD or info.get("LSMinimumSystemVersion") != "26.0":
        raise SystemExit("Unexpected build identity or deployment target")
    binary = built / "Contents/MacOS/DynamicNotch"
    if str(Path.home()).encode() in binary.read_bytes():
        raise SystemExit("The app binary still contains the build user's home path")

    staging.mkdir()
    app = staging / "DynamicNotch.app"
    run(["ditto", "--norsrc", "--noextattr", str(built), str(app)])
    run(["codesign", "--force", "--deep", "--sign", "-", "--timestamp=none", str(app)])
    run(["codesign", "--verify", "--deep", "--strict", str(app)])
    shutil.copyfile(ROOT / "LICENSE", staging / "LICENSE")
    shutil.copyfile(ROOT / "NOTICE.md", staging / "NOTICE.md")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {
        "repository": REPOSITORY,
        "source": f"{REPOSITORY}/tree/{commit}",
        "sourceTag": TAG,
        "sourceCommit": commit,
        "upstreamCommit": "deacd0f4275c73ae5d3328491d23d0e0dc0f6970",
        "version": info["CFBundleShortVersionString"],
        "build": BUILD,
        "architecture": "arm64",
        "minimumMacOS": "26.0",
        "signature": "ad-hoc",
        "notarized": False,
    }
    (staging / "BUILDINFO.json").write_text(json.dumps(manifest, indent=2) + "\n")
    run(["ditto", "-c", "-k", "--norsrc", "--noextattr", str(staging), str(archive)])
    with zipfile.ZipFile(archive) as bundle:
        packaged = plistlib.loads(bundle.read("DynamicNotch.app/Contents/Info.plist"))
        if packaged["CFBundleVersion"] != BUILD or bundle.testzip() is not None:
            raise SystemExit("Release archive verification failed")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    (output / "BUILDINFO.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built and verified {archive.name}\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
