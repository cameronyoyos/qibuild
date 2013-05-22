import qisys.qixml
import qisys.worktree
import qisrc.worktree

from qisrc.git_config import Remote


def test_read_git_configs(tmpdir, test_git):
    tmpdir.mkdir("foo")
    tmpdir.mkdir("bar")
    wt = qisys.worktree.WorkTree(tmpdir.strpath)
    foo_proj = wt.add_project("foo")
    bar_proj = wt.add_project("bar")

    git = test_git(foo_proj.path)
    git.initialize()

    git = test_git(bar_proj.path)
    git.initialize(branch="next")

    tmpdir.join(".qi").join("git.xml").write(""" \
<qigit>
 <project src="foo" >
    <branch name="master" tracks="origin" />
 </project>
 <project src="bar" >
    <branch name="next" tracks="origin" />
    <remote name="origin" url="git@srv:bar.git" />
    <remote name="gerrit" url="john@gerrit:bar.git" review="true"/>
 </project>
</qigit>
""")


    git_wt = qisrc.worktree.GitWorkTree(wt)
    git_projects = git_wt.git_projects
    assert len(git_projects) == 2

    foo = git_wt.get_git_project("foo")
    assert foo.src == "foo"
    assert len(foo.branches) == 1
    assert foo.branches[0].name == "master"
    assert foo.branches[0].tracks == "origin"
    assert not foo.remotes

    bar = git_wt.get_git_project("bar")
    assert bar.src == "bar"
    assert len(bar.branches) == 1
    assert len(bar.remotes) == 2
    origin = bar.remotes[0]
    assert origin.name == "origin"
    assert origin.url == "git@srv:bar.git"
    gerrit = bar.remotes[1]
    assert gerrit.name == "gerrit"
    assert origin.url == "git@srv:bar.git"



def test_git_configs_are_persistent(git_worktree):
    foo = git_worktree.create_git_project("foo")
    upstream = Remote()
    upstream.name = "upstream"
    upstream.url = "git@srv:bar.git"
    foo.configure_remote(upstream)
    foo.configure_branch("master", tracks="upstream")
    foo.save_config()

    def check_config(foo):
        assert len(foo.remotes) == 1
        upstream = foo.remotes[0]
        assert upstream.name == "upstream"
        assert upstream.url == "git@srv:bar.git"
        assert len(foo.branches) == 1
        master = foo.branches[0]
        assert master.name == "master"
        assert master.tracks == "upstream"

    check_config(foo)
    wt2 = qisrc.worktree.GitWorkTree(git_worktree.worktree)
    foo2 = wt2.get_git_project("foo")
    check_config(foo2)


