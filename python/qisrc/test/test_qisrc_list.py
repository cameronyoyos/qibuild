from qisys import ui

def test_list_tips_when_empty(qisrc_action, record_messages):
    qisrc_action("init")
    qisrc_action("list")
    assert ui.find_message("Tips")

def test_list_with_pattern(qisrc_action, record_messages):
    qisrc_action.git_worktree.create_git_project("foo")
    qisrc_action.git_worktree.create_git_project("baz")
    qisrc_action.git_worktree.create_git_project("foobar")
    record_messages.reset()
    qisrc_action("list", "foo.*")
    assert ui.find_message("foo")
    assert ui.find_message("foobar")
    assert not ui.find_message("baz")
