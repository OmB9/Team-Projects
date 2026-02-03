from pathlib import Path
import hashlib

# Return the MD5 fingerprint of a file
def compute_md5(file_path):
    md5 = hashlib.md5() # creates a new MD5 hashing object

    # opens the file for reading as raw bytes (rb). with ensures the file closes automatically
    with file_path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)  # reads up to 1MB of bytes from the file into chunk

            # if chunk is empty, then we have reached the end of file. break out of loop
            if not chunk:
                break

            md5.update(chunk) # feeds the chunk of bytes into the MD5 hashing object

    return md5.hexdigest() # returns the MD5 as a 32-character hex string.

# Parse a line of the manifest
def parse_manifest(line):
    line = line.strip() # strip whitespaces from both ends of the string variable line

    # if line is empty, return none
    if not line:
        return None

    parts = line.split("  ", 1) # split the line at two spaces since the manifest uses two spaces

    # if the split does not return 2 parts, return none
    if len(parts) != 2:
        return None

    expected_md5 = parts[0].strip() # isolate the first part of the line that holds the md5 hash
    filename = parts[1].strip() # isolate the second part of the line that holds the image file name

    # if the length of the md5 is not 32, return none
    if len(expected_md5) != 32:
        return None

    return expected_md5.lower(), filename # returns the expected md5 in lowercase along with the file name

# Verify the checksum of each image
def verify_checksum(folder):
    manifest_path = folder / "manifest.md5" # set the path of the manifest file

    # If path to manifest doesn't exist, throw error
    if not manifest_path.exists():
        raise SystemExit(f"Error: {manifest_path} not found.")

    lines = manifest_path.read_text().splitlines() # Put each line of manifest into a list
    failures = 0
    checked = 0

    # for each line in lines, parse the line to get the md5 and the file name
    # If function returns none, skip
    for line in lines:
        parsed_manifest = parse_manifest(line)
        if parsed_manifest is None:
            continue

        expected_md5, filename = parsed_manifest # put the md5 and filename into variables
        image_path = folder / filename # get the path for the image
        checked += 1

        # if image doesnt exist, increment failure count and print message
        if not image_path.exists():
            print(f"MISSING  {filename}")
            failures += 1
            continue

        actual_md5 = compute_md5(image_path)

        # if actual md5 is not as expected, increment error and print the difference 
        if actual_md5 != expected_md5:
            print(f"CHANGED  {filename}")
            print(f"  expected: {expected_md5}")
            print(f"  actual:   {actual_md5}")
            failures += 1

    # if checked count was 0, print error message as no checksum was checked
    if checked == 0:
        raise SystemExit("Error: manifest had no readable entries.")

    return checked, failures

if __name__ == "__main__":
    import sys

    # if argument is given, use that path. Otherwise, use current directory
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
    else:
        folder = Path(".")

    checked, failures = verify_checksum(folder)

    print("Summary:")
    print(f"  Checked:  {checked}")
    print(f"  Failures: {failures}")