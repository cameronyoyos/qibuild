import os
import zipfile

import qisys.command
import qibuild.worktree
import qibuild.cmake_builder
import qipy.worktree
import qipy.python_builder
import qilinguist.worktree
import qilinguist.builder
import qipkg.metabuilder

def test_meta_builder(qipkg_action):

    qipkg_action.add_test_project("a_cpp")
    qipkg_action.add_test_project("d_pkg")
    meta_pkg_proj = qipkg_action.add_test_project("meta_pkg")
    meta_pml = os.path.join(meta_pkg_proj.path, "meta_pkg.mpml")

    worktree = qipkg_action.worktree
    meta_pml_builder = qipkg.metabuilder.MetaPMLBuilder(worktree, meta_pml)

    meta_pml_builder.configure()
    meta_pml_builder.build()
    dump_syms = qisys.command.find_program("dump_syms")
    if dump_syms:
        with_breakpad = True
    else:
        with_breakpad = False
    pkg_path = meta_pml_builder.make_package(with_breakpad=with_breakpad)
    contents = list()
    archive = zipfile.ZipFile(pkg_path)
    for fileinfo in archive.infolist():
        contents.append(fileinfo.filename)
    if with_breakpad:
        assert contents == ['a-0.1.pkg', 'a-0.1-symbols.zip', 'd-0.1.pkg']
    else:
        assert contents == ['a-0.1.pkg', 'd-0.1.pkg']
