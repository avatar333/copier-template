from app.services import build_prefix_sequence_groups
from app.services.assignment_helpers import build_prefix_sequence_candidate_choices


def test_build_prefix_sequence_groups_uses_maximal_contiguous_runs():
    groups = build_prefix_sequence_groups(
        [
            "kafka01-stage-bry.platform.is",
            "kafka02-stage-bry.platform.is",
            "kafka03-stage-bry.platform.is",
            "kafka05-stage-bry.platform.is",
            "kafka06-stage-bry.platform.is",
            "kafka04-prod-bry.platform.is",
            "kafka04-stage-pkl.platform.is",
        ]
    )

    as_sets = {tuple(group.hosts) for group in groups}
    assert ("kafka01-stage-bry.platform.is", "kafka02-stage-bry.platform.is", "kafka03-stage-bry.platform.is") in as_sets
    assert ("kafka05-stage-bry.platform.is", "kafka06-stage-bry.platform.is") in as_sets
    assert all("kafka04-prod-bry.platform.is" not in group for group in as_sets)


def test_build_prefix_sequence_groups_handles_numeric_suffixes_anywhere():
    groups = build_prefix_sequence_groups(
        [
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-prod-bry.platform.is",
            "apisix-docker03-prod-bry.platform.is",
        ]
    )

    assert {tuple(group.hosts) for group in groups} == {
        (
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-prod-bry.platform.is",
            "apisix-docker03-prod-bry.platform.is",
        )
    }


def test_build_prefix_sequence_groups_does_not_mix_environment_or_site():
    groups = build_prefix_sequence_groups(
        [
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-stage-bry.platform.is",
            "apisix-docker03-prod-pkl.platform.is",
        ]
    )

    assert groups == []


def test_build_prefix_sequence_groups_splits_non_contiguous_runs():
    groups = build_prefix_sequence_groups(
        [
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-prod-bry.platform.is",
            "apisix-docker04-prod-bry.platform.is",
        ]
    )

    assert {tuple(group.hosts) for group in groups} == {
        (
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-prod-bry.platform.is",
        )
    }


def test_build_prefix_sequence_candidate_choices_prefer_leftmost_on_ties():
    choices = build_prefix_sequence_candidate_choices(
        [
            "app01-worker01-prod-bry.platform.is",
            "app02-worker02-prod-bry.platform.is",
        ]
    )

    choices_by_host = {choice.fqdn: choice for choice in choices}
    assert choices_by_host["app01-worker01-prod-bry.platform.is"].group_key == "app-worker01-prod-bry.platform.is"
    assert choices_by_host["app02-worker02-prod-bry.platform.is"].group_key == "app-worker02-prod-bry.platform.is"
    assert choices_by_host["app01-worker01-prod-bry.platform.is"].token_index == 0
    assert choices_by_host["app02-worker02-prod-bry.platform.is"].token_index == 0
