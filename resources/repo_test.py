#!/usr/bin/python3

'''
A set of classes for evaluating the code within a git repo.
Base classes can be created for performing tool-specific evaluation.
Several generic test classes are included that could be used in any
type of repository.
'''

# Manages file paths
import pathlib
# Shell utilities for copying, 
import shutil
import subprocess
import os
import sys
from enum import Enum
from git import Repo
import re


class repo_test():
    """ Class for performing a test on files within a repository.
    Each instance of this class represents a _single_ test with a single
    executable. Multiple tests can be performed by creating multiple instances
    of this test class.
    This is intended as a super class for custom test modules.
    """

    #def __init__(self, repo_test_suite, abort_on_error=True, process_output_filename = None):
    def __init__(self, abort_on_error=True, process_output_filename = None):
        """ Initialize the test module with a repo object """
        #self.rts = repo_test_suite
        #self.rts.add_test_module(self)
        self.abort_on_error = abort_on_error
        self.process_output_filename = process_output_filename

    def module_name(self):
        """ returns a string indicating the name of the module. Used for logging. """
        return "BASE MODULE"

    def perform_test(self, repo_test_suite):
        """ This function should be overridden by a subclass. It performs the test using
        the repo_test_suite object to obtain test-specific information. """ 
        return False

    def execute_command(self, repo_test_suite, proc_cmd, process_output_filename = None ):
        """ Completes a sub-process command. and print to a file and stdout.
        Args:
            proc_cmd -- The string command to be executed.
            proc_wd -- The directory in which the command should be executed. Note that the execution directory
                can be anywhere and not necessarily within the repository. If this is None, the self.working_path
                will be used.
            print_to_stdout -- If True, the output of the command will be printed to stdout.
            print_message -- If True, messages will be printed to stdout about the command being executed.
            process_output_filepath -- The file path to which the output of the command should be written.
                This can be None if no output file is wanted.
        Returns: the sub-process return code
        """
        
        fp = None
        if repo_test_suite.log_dir is not None and process_output_filename is not None:
            if not os.path.exists(self.repo_test_suite.log_dir):
                os.makedirs(self.repo_test_suite.log_dir)
            process_output_filepath = self.log_dir + '/' + process_output_filename
            fp = open(process_output_filepath, "w")
            if not fp:
                repo_test_suite.print_error("Error opening file for writing:", process_output_filepath)
                return -1
            repo_test_suite.print("Writing output to:", process_output_filepath)
        cmd_str = " ".join(proc_cmd)
        message = "Executing the following command in directory:"+str(repo_test_suite.working_path)+":"+str(cmd_str)
        repo_test_suite.print(message)
        if fp:
            fp.write(message+"\n")
        # Execute command		
        proc = subprocess.Popen(
            proc_cmd,
            cwd=repo_test_suite.working_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        for line in proc.stdout:
            if repo_test_suite.print_to_stdout:
                sys.stdout.write(line)
            if fp:
                fp.write(line)
                fp.flush()
        # Wait until process is done
        proc.communicate()
        return proc.returncode

class file_exists_test(repo_test):
    ''' Checks to see if files exist in a repo directory
    '''

    def __init__(self, repo_file_list, abort_on_error=True):
        '''  '''
        super().__init__(abort_on_error)
        self.repo_file_list = repo_file_list

    def module_name(self):
        return "File Check"

    def perform_test(self, repo_test_suite):
        return_val = True
        for repo_file in self.repo_file_list:
            file_path = repo_test_suite.working_path / repo_file
            if not os.path.exists(file_path):
                repo_test_suite.print_error(f'File does not exist: {file_path}')
                return_val = False
            repo_test_suite.print(f'File exists: {file_path}')
        return return_val

class make_test(repo_test):
    ''' Performs makefile rules
    '''

    def __init__(self, make_rule, generate_output_file = True, make_output_filename=None,
                 abort_on_error=True):
        '''  '''
        if generate_output_file and make_output_filename is None:
            make_output_filename = make_rule.replace(" ", "_") + '.log'
        super().__init__(abort_on_error=abort_on_error, process_output_filename=make_output_filename)
        self.make_rule = make_rule

    def module_name(self):
        return "Makefile"

    def perform_test(self, repo_test_suite):
        cmd = ["make", self.make_rule]
        return_val = self.execute_command(repo_test_suite, cmd)
        if return_val != 0:
            return False
        return True

class check_for_untracked_files(repo_test):
    ''' This tests the repo for any untracked files. Returns true if there are no untracked files.
    '''
    def __init__(self, ignore_ok = True):
        '''  '''
        super().__init__()
        self.ignore_ok = ignore_ok

    def module_name(self):
        return "Check for untracked GIT files"

    def perform_test(self, repo_test_suite):
        # TODO: look into using repo.untracked_files instead of git command

        untracked_files = repo_test_suite.repo.git.ls_files("--others", "--exclude-standard")
        if untracked_files:
            repo_test_suite.print_error(f'Untracked files found in repository:')
            files = untracked_files.splitlines()
            for file in files:
                repo_test_suite.print_error(f'  {file}')
            return False
        repo_test_suite.print(f'No untracked files found in repository')
        return True

class check_for_max_repo_files(repo_test):
    ''' 
    '''
    def __init__(self, max_dir_files):
        '''  '''
        super().__init__()
        self.max_dir_files = max_dir_files

    def module_name(self):
        return "Check for max tracked repo files"

    def perform_test(self, repo_test_suite):
        tracked_files = repo_test_suite.repo.git.ls_files(repo_test_suite.relative_repo_path).split('\n')
        n_tracked_files = len(tracked_files)
        repo_test_suite.print(f"{n_tracked_files} Tracked git files in {repo_test_suite.relative_repo_path}")
        if n_tracked_files > self.max_dir_files:
            repo_test_suite.print_error(f"  Too many tracked files")
            return False
        return True

class check_for_ignored_files(repo_test):
    ''' Checks to see if there are any ignored files in the repo directory.
    The intent is to make sure that these ignore files are remoted through a clean
    operation. Returns true if there are no ignored files in the directory.
    '''
    def __init__(self, check_path = None):
        '''  '''
        super().__init__()
        self.check_path = check_path

    def module_name(self):
        return "Check for ignored GIT files"

    def perform_test(self, repo_test_suite):
        if self.check_path is None:
            self.check_path = repo_test_suite.working_path
        # TODO: look into using repo.untracked_files instead of git command
        repo_test_suite.print(f'Checking for ignored files at {self.check_path}')
        ignored_files = repo_test_suite.repo.git.ls_files(self.check_path, "--others", "--ignored", "--exclude-standard")
        if ignored_files:
            repo_test_suite.print_error(f'Ignored files found in repository:')
            files = ignored_files.splitlines()
            for file in files:
                repo_test_suite.print_error(f'  {file}')
            return False
        repo_test_suite.print(f'No ignored files found in repository')
        return True

class check_for_uncommitted_files(repo_test):

    def __init__(self):
        '''  '''
        super().__init__()

    def module_name(self):
        return "Check for uncommitted GIT files"

    def perform_test(self, repo_test_suite):
        uncommitted_changes = repo_test_suite.repo.index.diff(None)
        modified_files = [item.a_path for item in uncommitted_changes if item.change_type == 'M']
        if modified_files:
            repo_test_suite.print_error(f'Uncommitted files found in repository:')
            for file in modified_files:
                repo_test_suite.print_error(f'  {file}')
            return False
        repo_test_suite.print(f'No uncommitted files found in repository')
        return True

class check_number_of_files(repo_test):
    ''' Counts the number of files in the repo directory.
    '''

    def __init__(self, max_files=sys.maxsize):
        '''  '''
        super().__init__()
        self.max_files = max_files

    def module_name(self):
        return "Count files in repo dir"

    def perform_test(self, repo_test_suite):
        uncommitted_files = repo_test_suite.repo.git.status("--suno")
        if uncommitted_files:
            repo_test_suite.print_error(f'Uncommitted files found in repository:')
            files = uncommitted_files.splitlines()
            for file in files:
                repo_test_suite.print_error(f'  {file}')
            return False
        repo_test_suite.print(f'No uncommitted files found in repository')
        return True

class list_git_commits(repo_test):
    ''' Prints the commits of the given directory in the repo.
    '''
    def __init__(self, check_path = None):
        '''  '''
        super().__init__()
        self.check_path = check_path

    def module_name(self):
        return "List Git Commits"

    def perform_test(self, repo_test_suite):
        if self.check_path is None:
            self.check_path = repo_test_suite.working_path
        relative_path = self.check_path.relative_to(repo_test_suite.repo_root_path)
        repo_test_suite.print(f'Checking for commits at {relative_path}')
        commits = list(repo_test_suite.repo.iter_commits(paths=relative_path))
        for commit in commits:
            commit_hash = commit.hexsha[:7]
            commit_message = commit.message.strip()
            commit_date = commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{commit_hash} - {commit_date} - {commit_message}")
        return True
