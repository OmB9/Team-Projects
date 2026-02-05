import os, glob
from pathlib import Path
from cryptography.fernet import Fernet

def generateKeyFile():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate a key
    key = Fernet.generate_key()

    # Save the key into a file
    with open(os.path.join(script_dir,'filekey.key'), 'wb') as f:
        f.write(key)
    
def encryptFiles(imagePath):
    
    # Load the key from the .key file
    with open(Path('filekey.key'), 'rb') as f:
        key = f.read()

    # Create a Fernet object using the key
    fernet = Fernet(key)

    # Open each file to be encrypted in binary read mode
    for filename in glob.glob(os.path.join(imagePath, '*.png')) + glob.glob(os.path.join(imagePath, '*.md5')):
        
        with open(os.path.join(os.getcwd(), filename), 'rb') as f:
            
            original = f.read()
            
            # Encrypt the file content
            encrypted = fernet.encrypt(original)
            
            # Overwrite the original file with the encrypted data
            with open(os.path.join(os.getcwd(), filename), 'wb') as f:
                f.write(encrypted)
            
        
        
if __name__ == "__main__":
    
    file_path = Path('filekey.key')

    if file_path.is_file():
        
        encryptFiles(Path('with_red_circles'))
        print("Files encrypted successfully.")
        
    else:
        generateKeyFile()
        print("Key file generated. Please run the program again to encrypt files.")