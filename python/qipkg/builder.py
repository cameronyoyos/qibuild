""" Builder for pml files """
import os
import sys
import zipfile

import qibuild.worktree

from qisys import ui
import qisys.qixml
import qibuild.breakpad

import qibuild.worktree
import qibuild.cmake_builder
import qipy.worktree
import qipy.python_builder
import qilinguist.worktree
import qilinguist.builder

class PMLBuilder(object):
    """ Build a package from a pml file """
    def __init__(self, worktree, pml_path):
        self.pml_path = pml_path
        self.base_dir = os.path.dirname(self.pml_path)
        self.manifest_xml = os.path.join(self.base_dir, "manifest.xml")
        if not os.path.exists(self.manifest_xml):
            raise Exception("%s does not exist" % self.manifest_xml)
        self.pkg_name = pkg_name(self.manifest_xml)


        self.worktree = worktree

        self.build_worktree = qibuild.worktree.BuildWorkTree(self.worktree)
        self.cmake_builder = qibuild.cmake_builder.CMakeBuilder(self.build_worktree)

        self.python_worktree = qipy.worktree.PythonWorkTree(self.worktree)
        self.python_builder = qipy.python_builder.PythonBuilder(
               self.python_worktree,
               build_worktree=self.build_worktree)

        self.linguist_worktree = qilinguist.worktree.LinguistWorkTree(self.worktree)
        self.linguist_builder = qilinguist.builder.QiLinguistBuilder(self.linguist_worktree)

        self.builders = [self.cmake_builder, self.python_builder, self.linguist_builder]

        # Hack: we need to parse some cmake variables when generating the
        # breakpad symbols, so we need to keep one build project around
        self.build_project = None

        self.pml_extra_files = list()
        self.cpp_installed_files = list()

        self.load_pml(pml_path)


    @property
    def stage_path(self):
        dot_qi = self.worktree.dot_qi
        build_config = self.cmake_builder.build_config
        name = build_config.build_directory(prefix="qipkg")
        return os.path.join(dot_qi, name)

    def load_pml(self, pml_path):
        for builder in self.builders:
            builder.projects = list()
        tree= qisys.qixml.read(pml_path)
        root = tree.getroot()
        qibuild_elems = root.findall("qibuild")
        for qibuild_elem in qibuild_elems:
            name = qisys.qixml.parse_required_attr(qibuild_elem, "name", pml_path)
            project = self.build_worktree.get_build_project(name, raises=True)
            self.cmake_builder.projects.append(project)
            self.build_project = project

        qipython_elems = root.findall("qipython")
        for qipython_elem in qipython_elems:
            name = qisys.qixml.parse_required_attr(qipython_elem, "name", pml_path)
            project = self.python_worktree.get_python_project(name, raises=True)
            self.python_builder.projects.append(project)

        qilinguist_elems = root.findall("qilinguist")
        for qilinguist_elem in qilinguist_elems:
            name = qisys.qixml.parse_required_attr(qilinguist_elem, "name", pml_path)
            project = self.linguist_worktree.get_linguist_project(name, raises=True)
            self.linguist_builder.projects.append(project)

        # For top, ressource, dialog, behavior, add stuff to self.file_list
        behaviors = root.find("BehaviorDescriptions")
        if behaviors is not None:
            for child in behaviors.findall("BehaviorDescription"):
                src = child.get("src")
                full_src = os.path.join(src, "behavior.xar")
                self.pml_extra_files.append(full_src)

        # Dialog
        dialogs = root.find("Dialogs")
        if dialogs is not None:
            for child in dialogs.findall("Dialog"):
                src = child.get("src")
                self.pml_extra_files.append(src)

        # Resources
        resources = root.find("Resources")
        if resources is not None:
            for child in resources.findall("File"):
                src = child.get("src")
                self.pml_extra_files.append(src)

        # Topics
        topics = root.find("Topics")
        if topics is not None:
            for child in topics.findall("Topic"):
                src = child.get("src")
                self.pml_extra_files.append(src)

        errors = list()
        for file in self.pml_extra_files:
            full_path = os.path.join(self.base_dir, file)
            if not os.path.exists(full_path):
                errors.append(file)
        if errors:
            mess = "Some files do not exist\n"
            for error in errors:
                mess += error + "\n"
            raise Exception(mess)

    def configure(self):
        """ Configure every project """
        for builder in self.builders:
            if isinstance(builder, qibuild.cmake_builder.CMakeBuilder):
                builder.dep_types=["build", "runtime", "test"]
            builder.configure()

    def build(self):
        """ Build every project """
        for builder in self.builders:
            builder.build()

    def install(self, destination):
        """ Install every project to the given destination """
        # Use every available builder to install
        for builder in self.builders:
            desc = desc_from_builder(builder)
            if builder.projects:
                ui.info(ui.bold, "-> Adding %s ..." % desc)
            if isinstance(builder, qibuild.cmake_builder.CMakeBuilder):
                builder.dep_types=["runtime"]
                self.cpp_installed_files = builder.install(destination,
                                                           components=["runtime"])
            else:
                builder.install(destination)

        # Also install self.pml_extra_files
        if self.pml_extra_files:
            ui.info(ui.bold, "-> Adding extra files ...")
        for src in self.pml_extra_files:
            full_src = os.path.join(self.base_dir, src)
            rel_src = os.path.relpath(full_src, self.base_dir)
            full_dest = os.path.join(destination, rel_src)
            qisys.sh.install(full_src, full_dest)

    def deploy(self, url):
        """ Deploy every project to the given url """
        qisys.remote.deploy(self.stage_path, url)

    def make_package(self, output=None, with_breakpad=False):
        """ Generate a package containing every project.

        :param: with_breakpad generate debug symbols for usage
                               with breakpad

        """
        # Make sure self.stage_path exists and is empty
        qisys.sh.rm(self.stage_path)
        qisys.sh.mkdir(self.stage_path, recursive=True)
        res = list()
        if not output:
            output = os.path.join(os.getcwd(), self.pkg_name + ".pkg")

        archive = zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED)
        #  Add the manifest
        manifest_xml = self.manifest_xml
        archive.write(manifest_xml, "manifest.xml")

        # Add everything from the staged path
        self.install(self.stage_path)
        ui.info(ui.bold, "-> Compressing package ...")
        to_add = list()
        for root,_, filenames in os.walk(self.stage_path):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path  = os.path.relpath(full_path, self.stage_path)
                to_add.append((full_path, rel_path))

        for i, (full_path, rel_path) in enumerate(to_add):
            n = len(to_add)
            if sys.stdout.isatty():
                percent = float(i) / n * 100
                sys.stdout.write("Done: %.0f%%\r" % percent)
                sys.stdout.flush()
            archive.write(full_path, rel_path)
        archive.close()

        symbols_archive = None
        if with_breakpad and self.build_project:
            ui.info(ui.bold, "-> Generating breakpad symbols ...")
            dirname = os.path.dirname(output)
            symbols_archive = os.path.join(dirname, self.pkg_name + "-symbols.zip")
            qibuild.breakpad.gen_symbol_archive(self.build_project,
                                                output=symbols_archive,
                                                base_dir=self.stage_path,
                                                file_list=self.cpp_installed_files)
            ui.info(ui.bold, "-> Symbols generated in", symbols_archive)
        ui.info(ui.bold, "-> Package generated in", output, "\n")
        if symbols_archive:
            return [output, symbols_archive]
        else:
            return [output]

    def __repr__(self):
        return "<PMLBuilder in %s>" % self.pml_path

def pkg_name(manifest_xml):
    "Return a string name-version"
    root = qisys.qixml.read(manifest_xml).getroot()
    uuid = root.get("uuid")
    version = root.get("version")
    output_name = "%s-%s" % (uuid, version)
    return output_name

def desc_from_builder(builder):
    class_name = builder.__class__.__name__
    if "CMakeBuilder" in class_name:
        return "C++ projects"
    if "Linguist" in class_name:
        return "translations"
    if "Python" in class_name:
        return "Python projects"
