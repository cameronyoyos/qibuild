## Copyright (C) 2011 Aldebaran Robotics

""" Launch automatic tests
"""

import os
import logging
import qibuild
import qibuild

def configure_parser(parser):
    """Configure parser for this action"""
    qibuild.parsers.toc_parser(parser)
    qibuild.parsers.build_parser(parser)
    parser.add_argument("project", nargs="?")
    parser.add_argument("--verbose-tests", action="store_true",
        help="Print output of the tests")
    parser.add_argument("--test-name",
        help="Only run one test")

def do(args):
    """Main entry point"""
    logger   = logging.getLogger(__name__)
    toc      = qibuild.toc_open(args.work_tree, args)

    if not args.project:
        project_name = qibuild.toc.project_from_cwd()
    else:
        project_name = args.project

    project = toc.get_project(project_name)
    logger.info("Testing %s in %s", project.name, toc.build_folder_name)
    toc.test_project(project,
        verbose_tests=args.verbose_tests,
        test_name=args.test_name)




