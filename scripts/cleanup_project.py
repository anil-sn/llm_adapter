#!/usr/bin/env python3
"""
Project Cleanup Script for llm_adapter
=============================================

This script performs comprehensive cleanup of the project by:
- Removing __pycache__ directories
- Removing PID files
- Clearing temporary and log files
- Cleaning build artifacts
- Removing stale/unnecessary files

Author: Anil Srirangapatna Nagesh
Version: 1.0
Created: 2026-04-27
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime


class ProjectCleaner:
    """Comprehensive project cleanup utility."""
    
    def __init__(self, project_root: str, dry_run: bool = False):
        """
        Initialize the project cleaner.
        
        Args:
            project_root: Root directory of the project
            dry_run: If True, only show what would be deleted without actually deleting
        """
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.stats = {
            'files_deleted': 0,
            'dirs_deleted': 0,
            'bytes_freed': 0,
            'errors': []
        }
    
    def get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        try:
            return path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    def delete_path(self, path: Path) -> bool:
        """
        Delete a file or directory.
        
        Args:
            path: Path to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if path.is_file():
                size = self.get_file_size(path)
                if self.dry_run:
                    print(f"  [DRY RUN] Would delete file: {path} ({size:,} bytes)")
                else:
                    path.unlink()
                    print(f"  Deleted file: {path} ({size:,} bytes)")
                self.stats['files_deleted'] += 1
                self.stats['bytes_freed'] += size
                return True
            elif path.is_dir():
                size = sum(self.get_file_size(f) for f in path.rglob('*') if f.is_file())
                if self.dry_run:
                    print(f"  [DRY RUN] Would delete directory: {path} ({size:,} bytes)")
                else:
                    shutil.rmtree(path)
                    print(f"  Deleted directory: {path} ({size:,} bytes)")
                self.stats['dirs_deleted'] += 1
                self.stats['bytes_freed'] += size
                return True
        except Exception as e:
            self.stats['errors'].append(f"Failed to delete {path}: {str(e)}")
            print(f"  ERROR: Failed to delete {path}: {str(e)}")
            return False
    
    def cleanup_pycache(self):
        """Remove all __pycache__ directories."""
        print("\n📦 Cleaning __pycache__ directories...")
        pycache_dirs = list(self.project_root.rglob('__pycache__'))
        
        if not pycache_dirs:
            print("  No __pycache__ directories found.")
            return
        
        for dir_path in pycache_dirs:
            # Skip .venv cache
            if '.venv' in str(dir_path):
                continue
            self.delete_path(dir_path)
    
    def cleanup_pid_files(self):
        """Remove all PID files."""
        print("\n📝 Cleaning PID files...")
        pid_patterns = ['*.pid', '*.lock', '*.sock']
        pid_files = []
        
        for pattern in pid_patterns:
            pid_files.extend(self.project_root.rglob(pattern))
        
        # Also check root directory for PID files
        for f in self.project_root.iterdir():
            if f.is_file() and (f.suffix == '.pid' or f.name.endswith('.pid')):
                pid_files.append(f)
        
        if not pid_files:
            print("  No PID files found.")
            return
        
        for pid_file in set(pid_files):
            self.delete_path(pid_file)
    
    def cleanup_logs(self):
        """Remove log files."""
        print("\n📋 Cleaning log files...")
        log_dirs = ['logs', 'log', '.logs']
        log_patterns = ['*.log', '*.log.*', '*.tmp', '*.temp']
        
        log_files = []
        
        # Check for log directories
        for log_dir in log_dirs:
            log_path = self.project_root / log_dir
            if log_path.exists() and log_path.is_dir():
                log_files.extend(log_path.rglob('*'))
        
        # Check for log files in root
        for pattern in log_patterns:
            log_files.extend(self.project_root.rglob(pattern))
        
        if not log_files:
            print("  No log files found.")
            return
        
        for log_file in set(log_files):
            if log_file.is_file():
                self.delete_path(log_file)
    
    def cleanup_build_artifacts(self):
        """Remove build artifacts and temporary files."""
        print("\n🔨 Cleaning build artifacts...")
        build_patterns = [
            '*.pyc', '*.pyo', '*.pyd', '*.so',
            '*.egg-info', '*.dist-info',
            '.pytest_cache', '.mypy_cache',
            '.ruff_cache', '.coverage',
            'coverage.xml', 'htmlcov',
            'dist/', 'build/', '*.egg',
            '.DS_Store', 'Thumbs.db'
        ]
        
        artifacts = []
        for pattern in build_patterns:
            if pattern.endswith('/'):
                artifacts.extend(self.project_root.rglob(pattern.rstrip('/')))
            else:
                artifacts.extend(self.project_root.rglob(pattern))
        
        if not artifacts:
            print("  No build artifacts found.")
            return
        
        for artifact in set(artifacts):
            if artifact.exists():
                self.delete_path(artifact)
    
    def cleanup_stale_md_files(self):
        """Remove stale markdown files but keep essential ones."""
        print("\n📄 Cleaning stale .md files...")
        
        # Essential markdown files to keep
        essential_files = {
            'README.md',
            'CONTRIBUTING.md',
            'CODE_OF_CONDUCT.md',
            'LICENSE',
            'CHANGELOG.md',
            'SECURITY.md',
            'SUPPORT.md',
            'VERIFICATION_REPORT.md',
            'PROFESSIONAL_REVIEW_READINESS.md'
        }
        
        md_files = list(self.project_root.rglob('*.md'))
        stale_files = []
        
        for md_file in md_files:
            # Skip files in docs/ directory
            if 'docs/' in str(md_file):
                continue
            
            # Skip essential files
            if md_file.name in essential_files:
                continue
            
            # Skip files in .github/ directory
            if '.github/' in str(md_file):
                continue
            
            stale_files.append(md_file)
        
        if not stale_files:
            print("  No stale .md files found.")
            return
        
        print(f"  Found {len(stale_files)} stale .md file(s):")
        for md_file in stale_files:
            print(f"    - {md_file.relative_to(self.project_root)}")
            self.delete_path(md_file)
    
    def cleanup_temp_files(self):
        """Remove temporary files."""
        print("\n🗑️  Cleaning temporary files...")
        temp_patterns = ['*.tmp', '*.temp', '*.swp', '*.swo', '*~', '*.bak', '*.backup']
        
        temp_files = []
        for pattern in temp_patterns:
            temp_files.extend(self.project_root.rglob(pattern))
        
        if not temp_files:
            print("  No temporary files found.")
            return
        
        for temp_file in set(temp_files):
            self.delete_path(temp_file)
    
    def update_gitignore(self):
        """Update .gitignore with comprehensive patterns."""
        print("\n📝 Updating .gitignore...")
        
        gitignore_path = self.project_root / '.gitignore'
        
        # Comprehensive .gitignore content
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environments
.venv/
venv/
ENV/
env/
.venv.bak/

# IDEs and Editors
.idea/
.vscode/
*.swp
*.swo
*~
.project
.pydevproject
.settings/
*.sublime-project
*.sublime-workspace

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Build Tools
*.pyc
*.pyo
*.pyd
.Python
pip-log.txt
pip-delete-this-directory.txt

# Jupyter Notebook
.ipynb_checkpoints

# Environment variables
.env
.env.local
.env.*.local
*.env

# Secrets and Credentials
*.pem
*.key
secrets/
credentials/
*.json.bak

# Logs
logs/
*.log

# OS Files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# PID and Lock Files
*.pid
*.lock
*.sock

# Temporary Files
*.tmp
*.temp
*.bak
*.backup
*~

# Database
*.db
*.sqlite
*.sqlite3

# Model Cache
*.bin
*.gguf
*.safetensors
*.pth
*.pt
*.ckpt

# Archive (deprecated code)
archive/

# Local Configuration
config/local.yaml
config/local.yml
config/*.local.*

# Profiling
*.prof
profile.out
cache.prof

# MyPy
.mypy_cache/
.dmypy.json
dmypy.json

# Ruff
.ruff_cache/

# Hydra
hydra/

# Output directories
output/
outputs/
results/

# Generated files
generated/
gen/
"""
        
        if self.dry_run:
            print(f"  [DRY RUN] Would update .gitignore at {gitignore_path}")
            return
        
        # Backup existing .gitignore
        if gitignore_path.exists():
            backup_path = gitignore_path.with_suffix('.gitignore.backup')
            shutil.copy2(gitignore_path, backup_path)
            print(f"  Backed up existing .gitignore to {backup_path.name}")
        
        # Write new .gitignore
        gitignore_path.write_text(gitignore_content)
        print(f"  Updated .gitignore with comprehensive patterns")
    
    def print_summary(self):
        """Print cleanup summary."""
        print("\n" + "="*60)
        print("CLEANUP SUMMARY")
        print("="*60)
        print(f"Files deleted:     {self.stats['files_deleted']}")
        print(f"Directories deleted: {self.stats['dirs_deleted']}")
        print(f"Space freed:       {self.stats['bytes_freed']:,} bytes ({self.stats['bytes_freed']/1024/1024:.2f} MB)")
        
        if self.stats['errors']:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        print("="*60)
        
        if self.dry_run:
            print("\n⚠️  This was a DRY RUN. No files were actually deleted.")
            print("   Run without --dry-run to perform actual cleanup.")
        else:
            print("\n✅ Cleanup completed successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Comprehensive project cleanup script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show what would be deleted)
  python cleanup_script.py --dry-run
  
  # Actual cleanup
  python cleanup_script.py
  
  # Clean specific project
  python cleanup_script.py --project /path/to/project
        """
    )
    
    parser.add_argument(
        '--project', '-p',
        type=str,
        default='.',
        help='Project root directory (default: current directory)'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Resolve project path
    project_root = Path(args.project).resolve()
    
    if not project_root.exists():
        print(f"ERROR: Project directory does not exist: {project_root}")
        return 1
    
    if not project_root.is_dir():
        print(f"ERROR: Path is not a directory: {project_root}")
        return 1
    
    print(f"\n{'='*60}")
    print(f"PROJECT CLEANUP SCRIPT")
    print(f"{'='*60}")
    print(f"Project: {project_root}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dry Run: {args.dry_run}")
    print(f"{'='*60}\n")
    
    # Create cleaner and run cleanup
    cleaner = ProjectCleaner(str(project_root), dry_run=args.dry_run)
    
    # Run all cleanup tasks
    cleaner.cleanup_pycache()
    cleaner.cleanup_pid_files()
    cleaner.cleanup_logs()
    cleaner.cleanup_build_artifacts()
    cleaner.cleanup_stale_md_files()
    cleaner.cleanup_temp_files()
    cleaner.update_gitignore()
    
    # Print summary
    cleaner.print_summary()
    
    return 0


if __name__ == '__main__':
    exit(main())
