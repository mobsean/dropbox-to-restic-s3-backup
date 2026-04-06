import os
import subprocess
import sys


class ResticBackup:
    def __init__(self, repository_path=None):
        """Initialize ResticBackup with repository path.
        
        If repository_path is not provided, it will be read from
        RESTIC_REPOSITORY environment variable or use default './restic-repo'.
        """
        if repository_path is None:
            repository_path = os.getenv('RESTIC_REPOSITORY', './restic-repo')
        self.repository_path = repository_path
        self.password = os.getenv('RESTIC_PASSWORD', '')

    def initialize_backup(self):
        """Initialize the backup repository if it doesn't exist."""
        try:
            result = subprocess.run(
                ['restic', 'init', '-r', self.repository_path],
                capture_output=True,
                text=True,
                env={**os.environ, 'RESTIC_PASSWORD': self.password}
            )
            if result.returncode == 0:
                print(f"Repository initialized at {self.repository_path}")
            elif 'already exists' in result.stderr or 'already exists' in result.stdout:
                print(f"Repository already exists at {self.repository_path}")
            else:
                print(f"Error initializing repository: {result.stderr}")
                sys.exit(1)
        except FileNotFoundError:
            print("Error: Restic is not installed or not in PATH")
            sys.exit(1)

    def add_to_backup(self, file_path):
        """Add a file or directory to the backup."""
        if not os.path.exists(file_path):
            print(f"Error: Path does not exist: {file_path}")
            return False

        try:
            result = subprocess.run(
                ['restic', 'backup', '-r', self.repository_path, file_path],
                env={**os.environ, 'RESTIC_PASSWORD': self.password}
            )
            if result.returncode == 0:
                print(f"Successfully added {file_path} to backup")
                return True
            else:
                print(f"Error adding to backup (exit code: {result.returncode})")
                return False
        except FileNotFoundError:
            print("Error: Restic is not installed or not in PATH")
            return False
