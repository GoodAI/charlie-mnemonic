# Making a release

This is a guide for making a release of Charlie Mnemonic.
Script `release/release.py` automates most of the process.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for building the docker image)
- Docker hub account and being [logged in](https://docs.docker.com/engine/reference/commandline/login/) (for pushing the
  docker image)
- [GitHub cli](https://github.com/cli/cli) (for creating releases)

## Release script

To run the release script:

```bash
python release/release.py <version>
```

Replace <version> with the desired version number for the release.

### What the Script Does

- Version Check: Verifies that the requested version is higher than the current version in version.txt.
- Git Clean Check: Ensures that the Git repository is clean (no uncommitted changes).
- Branch Check: Confirms that you are on the correct Git branch for the release.
- Unit Tests: Runs unit tests to ensure stability.
- Docker Image: Builds the Docker image and pushes it to Docker Hub, tagged with the specified version and latest.
- Git Tag: Creates a Git tag corresponding to the version.
- Artifact Creation: Generates an artifact with the docker-compose file and .bat files for Windows.
- GitHub Release: Creates a release on GitHub and uploads the artifact.
- Update Version: Updates version.txt with the new version and pushes this change.

### What the Script Does Not Do

- Release notes: You must manually add release notes to the GitHub release or if we use issues for new features, this
  can be generated automatically.
- It does not update LICENSES.txt. You must do this manually using generate_acknowledgements.py in case any new
  dependencies were added or updated.

```bash
pip install -U pip-licenses
pip-licenses --with-license-file --format=json > release/licenses.json
python release/generate_acknowledgments.py
```

## Advanced Script parameters

The release.py script accepts several parameters that control various aspects of the release process. These parameters
allow you to customize the release according to your requirements.
Please refer to the script help for the most up-to-date information.

```bash
python release/release.py <version> [--docker-repo <repo>] [--origin-name <name>] [--github-repo <repo>] [--release-notes <notes>] [--release-branch <branch>] [--force-push]
```

- version (Positional Argument)
    - Description: The version number for the release. It must follow Semantic Versioning.
    - Usage: python release/release.py 1.0.0

- --docker-repo
    - Default: goodaidev/charlie-mnemonic
    - Description: The name of the Docker repository where the Docker image will be pushed.
    - Usage: --docker-repo customrepo/myapp

- --origin-name
    - Default: opensource
    - Description: The name of the Git origin.
    - Usage: --origin-name myorigin

- --github-repo
    - Default: github.com/goodai/charlie-mnemonic
    - Description: The GitHub repository URL for the project.
    - Usage: --github-repo github.com/myuser/myproject

- --release-notes
    - Default: Release notes here
    - Description: Custom release notes for the GitHub release.
    - Usage: --release-notes "Fixed several bugs in this release"

- --release-branch
    - Default: dev
    - Description: The Git branch from which to release.
    - Usage: --release-branch master

- --force-push
    - Description: Enables force pushing to the repository. Use this option with caution as it can overwrite history.
    - Usage: --force-push

### Example

```bash
python release/release.py 1.2.3 --docker-repo myrepo/app --origin-name myorigin --github-repo github.com/myuser/myapp
--release-notes "Added new features" --release-branch master --force-push
```

This command will release version 1.2.3 of the application, using the specified Docker repository, origin name, GitHub
repository, release notes, release branch, and will force push if necessary.