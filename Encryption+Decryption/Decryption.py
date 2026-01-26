import os, glob
from pathlib import Path
from cryptography.fernet import Fernet

def decryptFiles(imagePath):
    
    # Load the key from the .key file
    with open('filekey.key', 'rb') as f:
        key = f.read()

    # Create a Fernet object using the key
    fernet = Fernet(key)

    # Open each file to be decrypted in binary read mode
    for filename in glob.glob(os.path.join(imagePath, '*.png')):
        
        with open(os.path.join(os.getcwd(), filename), 'rb') as f:
            
            encrypted = f.read()
            
            # Decrypt the file content
            decrypted = fernet.decrypt(encrypted)
            
            # Overwrite the original file with the decrypted data
            with open(os.path.join(os.getcwd(), filename), 'wb') as f:
                f.write(decrypted)
                
if __name__ == "__main__":
    
    file_path = Path('filekey.key')

    if file_path.is_file():
        
        decryptFiles(Path('with_red_circles'))
        print("Files decrypted successfully.")
        
    else:
        print("Key file not found. Cannot decrypt files.")