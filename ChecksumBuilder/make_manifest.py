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

# Find image files and sort them by name
def find_images(folder):
    images = []

    # look at each item within the folder. Folder is a path object so we need iterdir()
    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() == ".png":
            images.append(item)

    # for each path, take its file name, convert it to lower case, then sort by filename
    images.sort(key=lambda path: path.name.lower())
    return images

 # Write manifest.md5 and return how many images were listed
def make_manifest(folder):
    output_file = Path("manifest.md5") # set the output file name (where the manifest info will go)
    images = find_images(folder) # get a list of png files from the folder

    if len(images) == 0:
        raise RuntimeError(f"No images found in {folder}")

    # open the output file. w will overwite it if the file exists
    with output_file.open("w", newline="\n") as output:
        # loop over each image, writing the md5 of the image file + the name of the image file to the output file
        for image in images:
            output.write(f"{compute_md5(image)}  {image.name}\n")

    return len(images) # returns how many images were processed

if __name__ == "__main__":
    import sys

    # if argument is given, use that path. Otherwise, use current directory
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
    else:
        folder = Path(".")

    count = make_manifest(folder)
    print(f"Wrote manifest.md5 for {count} images.")