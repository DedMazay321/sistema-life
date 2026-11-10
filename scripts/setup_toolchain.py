from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".toolchain"
DOWNLOADS = TOOLS / "downloads"
DOWNLOADS.mkdir(parents=True, exist_ok=True)


def download(url: str, target: Path) -> None:
    if target.exists():
        print(f"Using existing archive {target.name}; checksum will be verified", flush=True)
        return
    print(f"Downloading {url}", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Sistema-App-Builder/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def setup_jdk() -> None:
    destination = TOOLS / "jdk-17"
    if (destination / "bin" / "java.exe").exists():
        print("JDK 17 already installed", flush=True)
        return
    metadata_url = (
        "https://api.adoptium.net/v3/assets/latest/17/hotspot"
        "?architecture=x64&image_type=jdk&os=windows&vendor=eclipse"
    )
    request = urllib.request.Request(metadata_url, headers={"User-Agent": "Sistema-App-Builder/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        assets = json.load(response)
    if not assets:
        raise RuntimeError("Adoptium returned no Windows x64 JDK 17 asset")
    package = assets[0]["binary"]["package"]
    archive = DOWNLOADS / package["name"]
    download(package["link"], archive)
    actual = sha256(archive)
    if actual.lower() != package["checksum"].lower():
        raise RuntimeError(f"JDK checksum mismatch: {actual}")
    print(f"JDK checksum verified: {actual}", flush=True)
    staging = TOOLS / "jdk-extract"
    if staging.exists():
        shutil.rmtree(staging)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(staging)
    roots = [path for path in staging.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("Unexpected JDK archive layout")
    shutil.move(str(roots[0]), destination)
    shutil.rmtree(staging)
    print(f"JDK installed at {destination}", flush=True)


def setup_android_command_tools() -> None:
    destination = TOOLS / "sdk" / "cmdline-tools" / "latest"
    if (destination / "bin" / "sdkmanager.bat").exists():
        print("Android command-line tools already installed", flush=True)
        return
    repository_url = "https://dl.google.com/android/repository/repository2-1.xml"
    request = urllib.request.Request(repository_url, headers={"User-Agent": "Sistema-App-Builder/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        repository = ET.fromstring(response.read())
    selected = None
    for remote_package in repository.iter():
        if not remote_package.tag.endswith("remotePackage"):
            continue
        if remote_package.attrib.get("path") != "cmdline-tools;latest":
            continue
        for archive in remote_package.iter():
            if not archive.tag.endswith("archive"):
                continue
            host_os = next((node.text for node in archive.iter() if node.tag.endswith("host-os")), None)
            if host_os != "windows":
                continue
            complete = next(node for node in archive.iter() if node.tag.endswith("complete"))
            url = next(node.text for node in complete if node.tag.endswith("url"))
            checksum = next(node.text for node in complete if node.tag.endswith("checksum"))
            selected = (url, checksum)
            break
    if selected is None:
        raise RuntimeError("Could not locate Windows Android command-line tools")
    relative_url, expected_checksum = selected
    url = relative_url if relative_url.startswith("https://") else "https://dl.google.com/android/repository/" + relative_url
    archive = DOWNLOADS / Path(relative_url).name
    download(url, archive)
    digest = hashlib.sha1()
    with archive.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual.lower() != expected_checksum.lower():
        raise RuntimeError(f"Android tools checksum mismatch: {actual}")
    print(f"Android tools SHA-1 checksum verified: {actual}", flush=True)
    staging = TOOLS / "android-tools-extract"
    if staging.exists():
        shutil.rmtree(staging)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(staging)
    source = staging / "cmdline-tools"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), destination)
    shutil.rmtree(staging)
    print(f"Android command-line tools installed at {destination}", flush=True)


if __name__ == "__main__":
    setup_jdk()
    setup_android_command_tools()
    print("TOOLCHAIN_READY", flush=True)
