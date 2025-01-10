import os
import shutil
from unittest import TestCase
from unittest.mock import Mock, patch

import git

from ..core import (
    clone_repository,
    add_and_commit,
    push_commits,
    set_git_config,
    create_and_push_branch,
)

class TestCore(TestCase):
    def setUp(self):
        self.test_dir = "/tmp/test_repo"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('git.Repo.clone_from')
    def test_clone_repository(self, mock_clone):
        repo_url = "https://github.com/test/repo.git"
        clone_repository(repo_url, self.test_dir)
        mock_clone.assert_called_once_with(repo_url, self.test_dir)

    @patch('git.Repo')
    @patch('src.utils.git_utils.core.generate_commit_message')
    def test_add_and_commit(self, mock_generate_msg, mock_repo):
        # Setup mock repository
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.is_dirty.return_value = True
        mock_generate_msg.return_value = "Test commit message"

        add_and_commit(self.test_dir)

        mock_instance.git.add.assert_called_once_with(A=True)
        mock_instance.index.commit.assert_called_once_with("Test commit message")

    @patch('git.Repo')
    def test_push_commits(self, mock_repo):
        # Setup mock repository
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.head.is_detached = False
        mock_instance.active_branch.name = "main"
        mock_instance.remotes.origin.url = "https://github.com/test/repo.git"
        mock_instance.head.commit = "commit1"
        mock_instance.refs = {"origin/main": Mock(commit="commit2")}

        result = push_commits(self.test_dir, "test_token")

        self.assertTrue(result)
        mock_instance.remotes.origin.push.assert_called_once()

    @patch('git.Repo')
    def test_set_git_config(self, mock_repo):
        # Setup mock repository
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_config = Mock()
        mock_instance.config_writer.return_value.__enter__.return_value = mock_config

        set_git_config("test_user", "test@email.com", self.test_dir)

        mock_config.set_value.assert_any_call("user", "name", "test_user")
        mock_config.set_value.assert_any_call("user", "email", "test@email.com")

    @patch('git.Repo')
    @patch('src.utils.git_utils.core.sync_fork_with_upstream')
    def test_create_and_push_branch(self, mock_sync, mock_repo):
        # Setup mock repository
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.bare = False
        mock_instance.heads = []
        mock_instance.remotes.origin.refs = []
        mock_instance.remotes.origin.url = "https://github.com/test/repo.git"

        create_and_push_branch(self.test_dir, "feature-branch", "test_token")

        mock_sync.assert_called_once_with(self.test_dir, "test_token")
        mock_instance.create_head.assert_called_once_with("feature-branch")
        mock_instance.heads.__getitem__.assert_called_with("feature-branch")

    @patch('git.Repo')
    def test_push_commits_no_changes(self, mock_repo):
        # Setup mock repository with no changes
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.head.is_detached = False
        mock_instance.active_branch.name = "main"
        mock_instance.remotes.origin.url = "https://github.com/test/repo.git"
        mock_instance.head.commit = "commit1"
        mock_instance.refs = {"origin/main": Mock(commit="commit1")}  # Same commit

        result = push_commits(self.test_dir, "test_token")

        self.assertFalse(result)
        mock_instance.remotes.origin.push.assert_not_called()

    @patch('git.Repo')
    def test_push_commits_detached_head(self, mock_repo):
        # Setup mock repository with detached HEAD
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.head.is_detached = True

        result = push_commits(self.test_dir, "test_token")

        self.assertFalse(result)
        mock_instance.remotes.origin.push.assert_not_called()

    @patch('git.Repo')
    @patch('src.utils.git_utils.core.generate_commit_message')
    def test_add_and_commit_no_changes(self, mock_generate_msg, mock_repo):
        # Setup mock repository with no changes
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.is_dirty.return_value = False

        add_and_commit(self.test_dir)

        mock_generate_msg.assert_not_called()
        mock_instance.git.add.assert_not_called()
        mock_instance.index.commit.assert_not_called()

    @patch('git.Repo')
    @patch('src.utils.git_utils.core.generate_commit_message')
    def test_add_and_commit_fallback_message(self, mock_generate_msg, mock_repo):
        # Setup mock repository
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.is_dirty.return_value = True
        mock_generate_msg.return_value = None  # Simulate message generation failure

        add_and_commit(self.test_dir)

        mock_instance.git.add.assert_called_once_with(A=True)
        mock_instance.index.commit.assert_called_once_with("agent bot commit")