import argparse
import os
import re
import subprocess
import sys
import zipfile


def semver_type(version: str) -> str:
    """Custom argparse type for validating Semantic Versioning."""
    semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[\da-zA-Z-]+(?:\.[\da-zA-Z-]+)*)?(?:\+[\da-zA-Z-]+(?:\.[\da-zA-Z-]+)*)?$"
    if not re.match(semver_pattern, version):
        raise argparse.ArgumentTypeError(
            "Version number does not follow Semantic Versioning. Format should be MAJOR.MINOR.PATCH."
        )
    return version


def run_command(
    command: str,
    error_message: str = "Command '{command}' exited with code: {return_code}",
) -> None:
    """Run a shell command and stream its output to stdout, including errors."""
    with subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    ) as proc:
        for line in proc.stdout:
            print(line, end="")

    if proc.returncode != 0:
        raise ValueError(
            error_message.format(command=command, return_code=proc.returncode)
        )


def zip_directory(path: str, zip_name: str) -> str:
    """Zip the contents of a directory."""
    final_path = os.path.join(path, zip_name)
    with zipfile.ZipFile(final_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith((".bat", ".yaml")):
                    zipf.write(os.path.join(root, file), file)
    return final_path


def release(
    version: str, docker_repo: str, github_repo: str, origin_name: str, release_dir: str
) -> None:
    """Perform the build, push, tagging, and release process."""
    zip_file = f"charlie-mnemonic-{version}.zip"
    print(f"Creating zip file {zip_file}")
    zip_directory(release_dir, zip_file)
    zip_path = os.path.join(release_dir, zip_file)

    print("Building and pushing Docker image")
    run_command(f"docker image build -t {docker_repo}:{version} .")

    run_command(f"docker tag {docker_repo}:{version} {docker_repo}:latest")

    print("Pushing to docker repository")
    run_command(f"docker push {docker_repo}:{version}")
    run_command(f"docker push {docker_repo}:latest")

    print("Creating git tag")
    run_command(f"git tag {version}")
    print("Pushing git tag")
    run_command(f"git push {origin_name} {version}")

    print("Creating GitHub release")
    run_command(
        f'gh release create {version} {zip_path} --repo {github_repo} --title "Release {version}" --notes "Release notes here"'
    )

    with open("version.txt", "w") as f:
        f.write(version)

    print(f"Successfully created and released version {version}")


def release_checks(new_version: str, current_version: str) -> None:
    from packaging import version

    if version.parse(current_version) >= version.parse(new_version):
        print(
            f"Error: Provided version {new_version} must be higher than the current version {current_version}."
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Docker and Git releases.")

    parser.add_argument(
        "version",
        type=semver_type,
        help="Version number for the release (must follow Semantic Versioning)",
    )

    parser.add_argument(
        "--docker-repo",
        default="goodaidev/charlie-mnemonic",
        help="Docker repository name (default: goodaidev/charlie-mnemonic)",
    )

    parser.add_argument(
        "--origin-name", default="opensource", help="Origin name (default: opensource)"
    )

    parser.add_argument(
        "--github-repo",
        default="github.com/goodai/charlie-mnemonic",
        help="GitHub repository URL (default: github.com/goodai/charlie-mnemonic)",
    )

    args = parser.parse_args()

    docker_repo = args.docker_repo
    github_repo = args.github_repo
    origin_name = args.origin_name
    release_dir = "release"
    with open("version.txt", "r") as f:
        current_version = f.read()

    release_checks(args.version, current_version=current_version)
    release(
        args.version,
        docker_repo,
        github_repo=github_repo,
        release_dir=release_dir,
        origin_name=origin_name,
    )


if __name__ == "__main__":
    main()
