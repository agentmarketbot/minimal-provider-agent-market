import subprocess
import sys
import json
from typing import Tuple
from urllib.parse import urlparse

def sync_fork(repo_path: str = '.') -> Tuple[bool, str]:
    """
    Sync a forked repository with its upstream repository.
    
    Args:
        repo_path: Path to the git repository. Defaults to current directory.
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Change to repo directory if specified
        if repo_path != '.':
            subprocess.run(['cd', repo_path], check=True)
            
        # Get the upstream remote if it exists
        remotes = subprocess.run(['git', 'remote', '-v'], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        
        if 'upstream' not in remotes.stdout:
            # Get the fork's parent repository URL
            repo_info = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                     capture_output=True,
                                     text=True,
                                     check=True)
            
            # Extract the parent repo URL (assumes GitHub URL format)
            origin_url = repo_info.stdout.strip()
            if 'github.com' not in origin_url:
                return False, "Not a GitHub repository"
                
            # Convert SSH URLs to HTTPS if needed
            if origin_url.startswith('git@github.com:'):
                origin_url = f"https://github.com/{origin_url.split('git@github.com:')[1]}"
            
            if origin_url.endswith('.git'):
                origin_url = origin_url[:-4]
                
            # Parse the GitHub URL to get owner and repo
            parsed_url = urlparse(origin_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) != 2:
                return False, "Invalid GitHub repository URL format"
            
            owner, repo = path_parts
            
            # Get API response for the fork's parent
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            parent_info = subprocess.run(['curl', '-s', api_url],
                                       capture_output=True,
                                       text=True,
                                       check=True)
            
            try:
                repo_data = json.loads(parent_info.stdout)
                if not repo_data.get('fork'):
                    return False, "Repository is not a fork"
                
                parent_data = repo_data.get('parent', {})
                if not parent_data:
                    return False, "Could not find parent repository information"
                
                # Add upstream remote
                upstream_url = parent_data.get('clone_url')
                if not upstream_url:
                    return False, "Could not find parent repository URL"
                
                subprocess.run(['git', 'remote', 'add', 'upstream', upstream_url],
                             check=True)
            except json.JSONDecodeError:
                return False, "Failed to parse GitHub API response"
            except Exception as e:
                return False, f"Error setting up upstream remote: {str(e)}"
        
        # Fetch upstream
        subprocess.run(['git', 'fetch', 'upstream'],
                      check=True)
        
        # Get current branch
        current = subprocess.run(['git', 'branch', '--show-current'],
                               capture_output=True,
                               text=True,
                               check=True)
        current_branch = current.stdout.strip()
        
        # Check if the branch exists in upstream
        ls_remote = subprocess.run(['git', 'ls-remote', '--heads', 'upstream', current_branch],
                                 capture_output=True,
                                 text=True)
        
        if not ls_remote.stdout.strip():
            # Branch doesn't exist in upstream, sync with main branch instead
            subprocess.run(['git', 'fetch', 'upstream', 'main:upstream-main'],
                         check=True)
            return True, "Current branch does not exist in upstream. Fetched upstream/main as reference."
        
        # Merge upstream changes if branch exists
        try:
            subprocess.run(['git', 'merge', f'upstream/{current_branch}'],
                         check=True)
            return True, "Successfully synced fork with upstream repository"
        except subprocess.CalledProcessError:
            # If merge fails, abort it and return error
            subprocess.run(['git', 'merge', '--abort'], capture_output=True)
            return False, "Failed to merge upstream changes. Please resolve conflicts manually."
        
    except subprocess.CalledProcessError as e:
        return False, f"Error syncing fork: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

if __name__ == '__main__':
    success, message = sync_fork()
    print(message)
    sys.exit(0 if success else 1)