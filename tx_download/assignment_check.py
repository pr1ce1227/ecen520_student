#!/usr/bin/python3

# Manages file paths
import pathlib
import sys

# Add to the system path the "resources" directory relative to the script that was run
resources_path = pathlib.Path(__file__).resolve().parent.parent  / 'resources'
sys.path.append( str(resources_path) )

import repo_test_suite
import repo_test
import test_suite_520

def main():
    ''' Main executable for script
    '''
    tester = test_suite_520.build_test_suite_520("tx_download",  min_err_commits = 3, max_repo_files = 20)
    tester.add_make_test("sim_debouncer")
    tester.add_make_test("sim_tx_top")
    tester.add_make_test("sim_tx_top_115200_even")
    tester.add_make_test("gen_tx_bit")
    tester.add_make_test("gen_tx_bit_115200_even")
    tester.add_build_test(repo_test.file_exists_test(["tx_top.bit", "tx_top_115200_even.bit",]))
    tester.run_tests()

    """
    parser = test_suite_520.test_args_520("tx_download_check assignment tester")
    args = parser.parse_args()
    checker = repo_test_suite.create_from_path()

    repo_test.list_git_commits(checker)
    test_suite_520.get_err_git_commits(checker,3)
    repo_test.check_for_max_repo_files(checker,20)
    repo_test.check_for_uncommitted_files(checker)
    if not args.nobuild:
        repo_test.make_test(checker,"sim_debouncer")
        repo_test.make_test(checker,"sim_tx_top")
        repo_test.make_test(checker,"sim_tx_top_115200_even")
        # TODO: need to make files for different implementation steps have different names
        repo_test.make_test(checker,"gen_tx_bit")
        repo_test.make_test(checker,"gen_tx_bit_115200_even")
        repo_test.file_exists_test(checker,["tx_top.bit", "tx_top_115200_even.bit",] )
        repo_test.check_for_untracked_files(checker)
    if not args.noclean:
        repo_test.make_test(checker,"clean")
        repo_test.check_for_ignored_files(checker)

    # Run tests
    checker.run_tests()
    """

if __name__ == "__main__":
    main()