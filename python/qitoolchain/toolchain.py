import os

from qisys import ui
import qisys.sh
import qitoolchain.database

class Toolchain(object):
    def __init__(self, name):
        self.name = name
        self.feed_url = None
        self.config_path = qisys.sh.get_config_path("qi", "toolchains",
                                                    "%s.xml" % self.name)

        self.register()
        self.load()

        db_path = qisys.sh.get_share_path("qi", "toolchains", "%s.xml" % self.name)
        if not os.path.exists(db_path):
            with open(db_path, "w") as fp:
                fp.write("<toolchain />")
        self.db = qitoolchain.database.DataBase(name, db_path)

    @property
    def packages(self):
        values = self.db.packages.values()
        values.sort()
        return values

    def load(self):
        tree = qisys.qixml.read(self.config_path)
        root = tree.getroot()
        self.feed_url = root.get("feed")

    def save(self):
        tree = qisys.qixml.read(self.config_path)
        root = tree.getroot()
        root.set("feed", self.feed_url)
        qisys.qixml.write(root, self.config_path)

    def register(self):
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as fp:
                fp.write("<toolchain />")

    def unregister(self):
        qisys.sh.rm(self.config_path)

    def update(self, feed_url=None):
        if feed_url is None:
            feed_url = self.feed_url
        self.db.update(feed_url)
        self.feed_url = feed_url
        self.save()

    def add_package(self, package):
        self.db.add_package(package)
        self.db.save()

    def remove_package(self, name):
        self.db.remove_package(name)
        self.db.save()

    def solve_deps(self, packages, dep_types=None):
        return self.db.solve_deps(packages, dep_types=dep_types)

    def get_package(self, name, raises=True):
        return self.db.get_package(name, raises=raises)

    def clean_cache(self):
        self.db.clean_cache()

    def remove(self):
        self.db.remove()
        self.unregister()

    @property
    def toolchain_file(self):
        toolchain_file_path = qisys.sh.get_cache_path("qi", "toolchains",
                                                     "toolchain-%s.cmake" % self.name)
        lines = ["# Autogenerated file. Do not edit\n",
                 "# Make sure we don't keep adding elements to this list:\n",
                 "set(CMAKE_PREFIX_PATH "" CACHE INTERNAL "" FORCE)\n",
                 "set(CMAKE_FRAMEWORK_PATH "" CACHE INTERNAL "" FORCE)\n"
        ]

        for package in self.packages:
            if package.toolchain_file:
                tc_file = qisys.sh.to_posix_path(package.toolchain_file)
                lines.append('include("%s")\n' % tc_file)
        for package in self.packages:
            package_path = qisys.sh.to_posix_path(package.path)
            lines.append('list(INSERT CMAKE_PREFIX_PATH 0 "%s")\n' % package_path)
            # For some reason CMAKE_FRAMEWORK_PATH does not follow CMAKE_PREFIX_PATH
            # (well, you seldom use frameworks when cross-compiling ...), so we
            # need to change this variable too
            lines.append('list(INSERT CMAKE_FRAMEWORK_PATH 0 "%s")\n' % package_path)

        oldlines = list()
        if os.path.exists(toolchain_file_path):
            with open(toolchain_file_path, "r") as fp:
                oldlines = fp.readlines()

        # Do not write the file if it's the same
        if lines == oldlines:
            return toolchain_file_path

        with open(toolchain_file_path, "w") as fp:
            lines = fp.writelines(lines)

        return toolchain_file_path

    def get_sysroot(self):
        """ Get the sysroot of the toolchain.
        Assume that one and exactly one of the packages inside
        the toolchain has a 'sysroot' attribute

        """
        for package in self.packages:
            if package.sysroot:
                return package.sysroot

    def get_cross_gdb(self):
        """ Get the cross-gdb path from the toolchain.
        Assume that one and exactly one of the packages inside
        the toolchain has a 'cross_gdb' attribute

        """
        for package in self.packages:
            if package.cross_gdb:
                return package.cross_gdb

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        res  = "Toolchain %s\n" % self.name
        if self.feed_url:
            res += "Using feed from %s\n" % self.feed_url
        else:
            res += "No feed\n"
        if self.packages:
            res += "  Packages:\n"
        else:
            res += "No packages\n"
        sorted_packages = sorted(self.packages)
        for package in sorted_packages:
            res += ui.indent(package.name, 2)
            if package.version:
                res += " " + package.version
            res += "\n"
            if package.path:
                res +=  ui.indent("in " + package.path, 3) + "\n"
        return res

def get_tc_names():
    configs_path = qisys.sh.get_config_path("qi", "toolchains")
    if not os.path.exists(configs_path):
        return list()
    contents = os.listdir(configs_path)
    contents = [x for x in contents if x.endswith(".xml")]
    contents.sort()
    return [x.replace(".xml", "") for x in contents]

def get_default_packages_path(tc_name):
    root = qisys.sh.get_share_path("qi", "toolchains")
    res = os.path.join(root, tc_name)
    qisys.sh.mkdir(res, recursive=True)
    return res
