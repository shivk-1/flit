"""Validator tests — the cross-domain merge rules work today, no .flp needed."""

from flit import validator


def test_clean_project_has_no_issues():
    domains = {
        "channels": {"channels": [{"id": "ch_1", "name": "Kick"}]},
        "patterns": {"patterns": [{"id": "pat_0", "name": "Beat",
                                   "notes": [{"channel": "ch_1", "position": 0,
                                              "length": 24, "key": 60}]}]},
        "arrangement": {"arrangements": [{"id": "arr_0", "tracks": [
            {"index": 1, "items": [{"id": "pi_0", "kind": "pattern",
                                    "ref": "pat_0", "start": 0, "length": 96}]}]}]},
        "mixer": {"tracks": [{"index": 0, "name": "Master", "routes": []}]},
        "automation": {"automation_clips": []},
        "manifest": {"assets": {}},
        "metadata": {"tempo": 140},
    }
    assert validator.validate(domains) == []


def test_orphan_note_detected():
    domains = {
        "channels": {"channels": []},  # ch_1 deleted
        "patterns": {"patterns": [{"id": "pat_0", "notes": [
            {"channel": "ch_1", "position": 0, "length": 24, "key": 60}]}]},
    }
    issues = validator.validate(domains)
    assert any(i.rule == "orphan_note" and i.severity == "error" for i in issues)


def test_orphan_playlist_pattern_detected():
    domains = {
        "patterns": {"patterns": []},  # pat_0 deleted
        "arrangement": {"arrangements": [{"id": "arr_0", "tracks": [
            {"index": 1, "items": [{"id": "pi_0", "kind": "pattern",
                                    "ref": "pat_0", "start": 0, "length": 96}]}]}]},
    }
    issues = validator.validate(domains)
    assert any(i.rule == "orphan_playlist_pattern" for i in issues)


def test_overlapping_items_detected():
    domains = {
        "arrangement": {"arrangements": [{"id": "arr_0", "tracks": [
            {"index": 1, "items": [
                {"id": "a", "kind": "pattern", "ref": "p", "start": 0, "length": 100},
                {"id": "b", "kind": "pattern", "ref": "p", "start": 50, "length": 100},
            ]}]}]},
        "patterns": {"patterns": [{"id": "p", "notes": []}]},
    }
    issues = validator.validate(domains)
    assert any(i.rule == "overlapping_items" for i in issues)
