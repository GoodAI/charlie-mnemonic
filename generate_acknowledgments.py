import json
from typing import List, Dict


def group_by_license(packages: List[Dict]) -> Dict[str, List[Dict]]:
    """Group packages by their licenses."""
    grouped = {}
    for package in packages:
        license_name = package.get("License")
        if license_name not in grouped:
            grouped[license_name] = []
        grouped[license_name].append(package)
    return grouped


def create_licenses_txt(grouped_packages: Dict[str, List[Dict]], output_file: str):
    """Create a LICENSES.txt file from grouped packages."""
    with open(output_file, "w") as file:
        for license_name, packages in grouped_packages.items():
            file.write(f"License: {license_name}\n")
            file.write("Packages:\n")
            for package in packages:
                file.write(f"  - {package['Name']} {package['Version']}\n")
            file.write("\n")


def create_licenses_txt_2(packages: List[Dict], output_file: str):
    """Create a LICENSES.txt file from grouped packages."""
    with open(output_file, "w") as file:
        for package in packages:
            file.write(f"{package['Name']} {package['Version']}\n")
            file.write(f"{package['License']}\n\n")
            file.write(f"{package['LicenseText']}\n\n\n")


if __name__ == "__main__":
    try:
        with open("licenses.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(
            "Please run `pip-licenses --with-license-file --format=json > licenses.json` first (install pip-licenses if needed)."
        )
        exit(1)
    create_licenses_txt_2(data, "LICENSES.txt")
