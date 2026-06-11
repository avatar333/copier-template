from __future__ import annotations

from types import SimpleNamespace

from app.services.assignment_engine import AssignmentEngine, _pick_prefix_group_user
from app.services.assignment_helpers import PrefixSequenceGroupDetail


def make_user(
    user_id: int,
    first_name: str,
    last_name: str,
    is_admin: bool = False,
    assign_only_pets: bool = False,
    assign_only_production_pets: bool = False,
    assign_only_non_production_pets: bool = False,
):
    return SimpleNamespace(
        id=user_id,
        first_name=first_name,
        last_name=last_name,
        is_admin=is_admin,
        assign_only_pets=assign_only_pets,
        assign_only_production_pets=assign_only_production_pets,
        assign_only_non_production_pets=assign_only_non_production_pets,
    )


def build_engine(
    users,
    hosts,
    pet_map=None,
    seed=7,
    min_prefix_group_size=2,
    prefix_group_randomness_window=1,
    pool_name=None,
):
    return AssignmentEngine(
        users=users,
        all_hosts=hosts,
        pet_map=pet_map or {},
        config={
            "random_seed": seed,
            "min_prefix_group_size": min_prefix_group_size,
            "prefix_group_randomness_window": prefix_group_randomness_window,
        },
        pool_name=pool_name,
    )


class ReverseShuffleRandom:
    def __init__(self):
        self.choice_inputs: list[list[int]] = []

    def choice(self, seq):
        values = list(seq)
        self.choice_inputs.append(values)
        return values[-1]

    def shuffle(self, seq):
        seq.reverse()


def assigned_items(result, user_id):
    return result.assignments_by_user[user_id]


PRODUCTION_JBOSS_HOSTS = [
    "jboss01-prod-bry.platform.is",
    "jboss02-prod-pkl.platform.is",
    "jboss03-prod-bry.platform.is",
    "jboss04-prod-pkl.platform.is",
    "jboss05-prod-bry.platform.is",
    "jboss06-prod-pkl.platform.is",
]

NON_PRODUCTION_JBOSS_HOSTS = [
    "jboss01-dev-bry.platform.is",
    "jboss02-dev-pkl.platform.is",
    "jboss03-dev-bry.platform.is",
    "jboss04-dev-pkl.platform.is",
    "jboss05-dev-bry.platform.is",
    "jboss06-dev-pkl.platform.is",
]


def flatten_assignments(result):
    return [
        (user_id, item)
        for user_id, items in result.assignments_by_user.items()
        for item in items
    ]


def test_zero_users_returns_error_result():
    result = build_engine([], ["host01.example.com"]).generate()

    assert result.has_error is True
    assert "No local users" in (result.error_message or "")
    assert result.assignments_by_user == {}


def test_zero_hosts_returns_warning_and_empty_assignments():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(users, []).generate()

    assert any("No hosts were returned" in warning for warning in result.warnings)
    assert result.all_available_hosts == []
    assert result.remaining_unassigned_hosts == []
    assert all(not items for items in result.assignments_by_user.values())


def test_pet_priority_and_pool_removal():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "web01.example.com",
            "web02.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
    ).generate()

    assert assigned_items(result, 1)[0].fqdn == "pet01.example.com"
    assert assigned_items(result, 1)[0].source_type == "pet"
    assert "pet01.example.com" not in result.remaining_unassigned_hosts


def test_assign_only_production_pets_user_receives_only_in_pool_production_pets():
    users = [
        make_user(1, "Admin", "User", assign_only_production_pets=True),
        make_user(2, "Regular", "User"),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "db01.example.com",
            "db02.example.com",
            "misc01.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="production",
    ).generate()

    user_one_sources = {item.source_type for item in assigned_items(result, 1)}
    assert user_one_sources == {"pet"}
    assert any(item.fqdn == "pet01.example.com" for item in assigned_items(result, 1))
    assert all(item.source_type != "pet" for item in assigned_items(result, 2))
    assert all(item.source_type in {"prefix_sequence", "random"} for item in assigned_items(result, 2))


def test_all_assign_only_production_pets_users_do_not_receive_non_pet_production_hosts():
    users = [
        make_user(1, "Admin", "User", assign_only_production_pets=True),
        make_user(2, "Regular", "User", assign_only_production_pets=True),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "db01.example.com",
            "db02.example.com",
            "misc01.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="production",
    ).generate()

    assert any("Assign ONLY Production Pets" in warning for warning in result.warnings)
    assert [item.fqdn for item in assigned_items(result, 1)] == ["pet01.example.com"]
    assert assigned_items(result, 2) == []
    assert sorted(result.remaining_unassigned_hosts) == [
        "db01.example.com",
        "db02.example.com",
        "misc01.example.com",
    ]


def test_production_assignment_ignores_assign_only_non_production_pets_flag():
    users = [
        make_user(1, "Admin", "User", assign_only_non_production_pets=True),
        make_user(2, "Regular", "User", assign_only_production_pets=True),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "db01.example.com",
            "db02.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="production",
    ).generate()

    assert any(item.source_type != "pet" for item in assigned_items(result, 1))


def test_production_assignment_excludes_assign_only_production_pets_user_from_prefix_groups():
    users = [
        make_user(1, "Admin", "User", assign_only_production_pets=True),
        make_user(2, "Regular", "User"),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "kafka01-stage-bry.platform.is",
            "kafka02-stage-bry.platform.is",
            "kafka03-stage-bry.platform.is",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="production",
    ).generate()

    assert [item.source_type for item in assigned_items(result, 1)] == ["pet"]
    assert all(item.source_type == "prefix_sequence" for item in assigned_items(result, 2))


def test_non_production_assignment_excludes_assign_only_non_production_pets_user_from_random_hosts():
    users = [
        make_user(1, "Admin", "User", assign_only_non_production_pets=True),
        make_user(2, "Regular", "User"),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "web-a.example.com",
            "web-b.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="non_production",
    ).generate()

    assert [item.source_type for item in assigned_items(result, 1)] == ["pet"]
    assert all(item.source_type == "random" for item in assigned_items(result, 2))


def test_non_production_assignment_excludes_assign_only_non_production_pets_user_from_prefix_groups():
    users = [
        make_user(1, "Admin", "User", assign_only_non_production_pets=True),
        make_user(2, "Regular", "User"),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "kafka01-stage-bry.platform.is",
            "kafka02-stage-bry.platform.is",
            "kafka03-stage-bry.platform.is",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="non_production",
    ).generate()

    assert [item.source_type for item in assigned_items(result, 1)] == ["pet"]
    assert all(item.source_type == "prefix_sequence" for item in assigned_items(result, 2))


def test_non_production_assignment_ignores_assign_only_production_pets_flag():
    users = [
        make_user(1, "Admin", "User", assign_only_production_pets=True),
        make_user(2, "Regular", "User", assign_only_non_production_pets=True),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "misc01.example.com",
            "misc02.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="non_production",
    ).generate()

    assert any(item.source_type != "pet" for item in assigned_items(result, 1))


def test_unknown_pet_warning_does_not_crash():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        ["web01.example.com"],
        pet_map={1: {"missing.example.com"}},
    ).generate()

    assert any("missing.example.com" in warning for warning in result.warnings)
    assert any(item.fqdn == "web01.example.com" for item in assigned_items(result, 1) + assigned_items(result, 2))


def test_duplicate_pet_conflict_is_warned_and_left_unassigned():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        ["shared.example.com"],
        pet_map={1: {"shared.example.com"}, 2: {"shared.example.com"}},
    ).generate()

    assert any("multiple users" in warning for warning in result.warnings)
    assert all(item.fqdn != "shared.example.com" for items in result.assignments_by_user.values() for item in items)
    assert "shared.example.com" in result.remaining_unassigned_hosts


def test_prefix_sequence_grouping_keeps_matching_runs_together():
    users = [make_user(1, "Admin", "User")]
    result = build_engine(
        users,
        [
            "kafka01-stage-bry.platform.is",
            "kafka02-stage-bry.platform.is",
            "kafka03-stage-bry.platform.is",
            "kafka04-prod-bry.platform.is",
            "kafka04-stage-pkl.platform.is",
        ],
        seed=11,
    ).generate()

    prefix_items = [item for item in assigned_items(result, 1) if item.source_type == "prefix_sequence"]
    assert [item.fqdn for item in prefix_items] == [
        "kafka01-stage-bry.platform.is",
        "kafka02-stage-bry.platform.is",
        "kafka03-stage-bry.platform.is",
    ]
    assert any(item.fqdn == "kafka04-prod-bry.platform.is" and item.source_type == "random" for item in assigned_items(result, 1))
    assert any(item.fqdn == "kafka04-stage-pkl.platform.is" and item.source_type == "random" for item in assigned_items(result, 1))
    assert result.grouped_prefix_sequences[0]["group_key"] == "kafka-stage-bry.platform.is"
    assert result.grouped_prefix_sequences[0]["source_name"] == "kafka-stage-bry.platform.is[01-03]"


def test_apisix_docker_sequence_groups_together_for_one_user():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-prod-bry.platform.is",
            "apisix-docker03-prod-bry.platform.is",
            "misc01.example.com",
        ],
        seed=17,
    ).generate()

    prefix_items = [item for items in result.assignments_by_user.values() for item in items if item.source_type == "prefix_sequence"]
    assert [item.fqdn for item in prefix_items] == [
        "apisix-docker01-prod-bry.platform.is",
        "apisix-docker02-prod-bry.platform.is",
        "apisix-docker03-prod-bry.platform.is",
    ]
    assert all(item.source_name == "apisix-docker-prod-bry.platform.is[01-03]" for item in prefix_items)
    assert len({user_id for user_id, items in result.assignments_by_user.items() if any(item.source_type == "prefix_sequence" for item in items)}) == 1
    assert result.grouped_prefix_sequences[0]["group_key"] == "apisix-docker-prod-bry.platform.is"
    assert result.grouped_prefix_sequences[0]["source_name"] == "apisix-docker-prod-bry.platform.is[01-03]"


def test_production_jboss_special_group_is_assigned_unsplit():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        PRODUCTION_JBOSS_HOSTS + ["misc01.example.com"],
        seed=31,
        pool_name="production",
    ).generate()

    special_items = [
        (user_id, item)
        for user_id, item in flatten_assignments(result)
        if item.fqdn in PRODUCTION_JBOSS_HOSTS
    ]

    assert [item.fqdn for _, item in special_items] == PRODUCTION_JBOSS_HOSTS
    assert {user_id for user_id, _ in special_items} == {special_items[0][0]}
    assert all(item.source_type == "prefix_sequence" for _, item in special_items)
    assert all(item.source_name == "jboss-production-special" for _, item in special_items)
    assert any(group["source_name"] == "jboss-production-special" for group in result.grouped_prefix_sequences)


def test_non_production_jboss_special_group_is_assigned_unsplit():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        NON_PRODUCTION_JBOSS_HOSTS + ["misc01.example.com"],
        seed=37,
        pool_name="non_production",
    ).generate()

    special_items = [
        (user_id, item)
        for user_id, item in flatten_assignments(result)
        if item.fqdn in NON_PRODUCTION_JBOSS_HOSTS
    ]

    assert [item.fqdn for _, item in special_items] == NON_PRODUCTION_JBOSS_HOSTS
    assert {user_id for user_id, _ in special_items} == {special_items[0][0]}
    assert all(item.source_type == "prefix_sequence" for _, item in special_items)
    assert all(item.source_name == "jboss-non-production-special" for _, item in special_items)
    assert any(group["source_name"] == "jboss-non-production-special" for group in result.grouped_prefix_sequences)


def test_jboss_special_groups_are_pool_specific():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    production_hosts_in_non_prod = build_engine(
        users,
        PRODUCTION_JBOSS_HOSTS,
        seed=41,
        pool_name="non_production",
    ).generate()
    non_prod_hosts_in_prod = build_engine(
        users,
        NON_PRODUCTION_JBOSS_HOSTS,
        seed=43,
        pool_name="production",
    ).generate()

    assert all(
        item.source_name != "jboss-production-special"
        for _, item in flatten_assignments(production_hosts_in_non_prod)
    )
    assert all(
        item.source_name != "jboss-non-production-special"
        for _, item in flatten_assignments(non_prod_hosts_in_prod)
    )
    assert production_hosts_in_non_prod.grouped_prefix_sequences == []
    assert non_prod_hosts_in_prod.grouped_prefix_sequences == []


def test_partial_jboss_special_group_warns_and_assigns_present_hosts_together():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    present_hosts = PRODUCTION_JBOSS_HOSTS[:3]
    result = build_engine(
        users,
        present_hosts + ["misc01.example.com"],
        seed=47,
        pool_name="production",
    ).generate()

    special_items = [
        (user_id, item)
        for user_id, item in flatten_assignments(result)
        if item.fqdn in present_hosts
    ]

    assert [item.fqdn for _, item in special_items] == present_hosts
    assert {user_id for user_id, _ in special_items} == {special_items[0][0]}
    assert all(item.source_name == "jboss-production-special" for _, item in special_items)
    warning = next(warning for warning in result.warnings if "missing expected hosts" in warning)
    for missing_host in PRODUCTION_JBOSS_HOSTS[3:]:
        assert missing_host in warning


def test_no_jboss_special_group_or_warning_when_no_special_hosts_present():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        ["misc01.example.com", "misc02.example.com"],
        seed=53,
        pool_name="production",
    ).generate()

    assert all("Special JBoss group" not in warning for warning in result.warnings)
    assert all(group["source_name"] != "jboss-production-special" for group in result.grouped_prefix_sequences)


def test_production_jboss_pet_keeps_pet_owner_and_assigns_remaining_special_group():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    pet_host = PRODUCTION_JBOSS_HOSTS[0]
    result = build_engine(
        users,
        PRODUCTION_JBOSS_HOSTS,
        pet_map={1: {pet_host}},
        seed=59,
        pool_name="production",
    ).generate()

    assert any(item.fqdn == pet_host and item.source_type == "pet" for item in assigned_items(result, 1))
    special_items = [
        (user_id, item)
        for user_id, item in flatten_assignments(result)
        if item.source_name == "jboss-production-special"
    ]
    assert [item.fqdn for _, item in special_items] == PRODUCTION_JBOSS_HOSTS[1:]
    assert {user_id for user_id, _ in special_items} == {special_items[0][0]}
    assert any("pet ownership takes priority" in warning and pet_host in warning for warning in result.warnings)


def test_non_production_jboss_pet_keeps_pet_owner_and_assigns_remaining_special_group():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    pet_host = NON_PRODUCTION_JBOSS_HOSTS[0]
    result = build_engine(
        users,
        NON_PRODUCTION_JBOSS_HOSTS,
        pet_map={2: {pet_host}},
        seed=61,
        pool_name="non_production",
    ).generate()

    assert any(item.fqdn == pet_host and item.source_type == "pet" for item in assigned_items(result, 2))
    special_items = [
        (user_id, item)
        for user_id, item in flatten_assignments(result)
        if item.source_name == "jboss-non-production-special"
    ]
    assert [item.fqdn for _, item in special_items] == NON_PRODUCTION_JBOSS_HOSTS[1:]
    assert {user_id for user_id, _ in special_items} == {special_items[0][0]}
    assert any("pet ownership takes priority" in warning and pet_host in warning for warning in result.warnings)


def test_assign_only_pets_user_can_own_special_jboss_pet_but_not_receive_group_members():
    users = [
        make_user(1, "Admin", "User", assign_only_production_pets=True),
        make_user(2, "Regular", "User"),
    ]
    pet_host = PRODUCTION_JBOSS_HOSTS[0]
    result = build_engine(
        users,
        PRODUCTION_JBOSS_HOSTS,
        pet_map={1: {pet_host}},
        seed=63,
        pool_name="production",
    ).generate()

    assert any(item.fqdn == pet_host and item.source_type == "pet" for item in assigned_items(result, 1))
    special_items = [
        (user_id, item)
        for user_id, item in flatten_assignments(result)
        if item.source_name == "jboss-production-special"
    ]
    assert [item.fqdn for _, item in special_items] == PRODUCTION_JBOSS_HOSTS[1:]
    assert {user_id for user_id, _ in special_items} == {2}
    assert all(item.source_type == "pet" for item in assigned_items(result, 1))


def test_all_assign_only_non_production_pets_users_leave_non_pet_hosts_unassigned():
    users = [
        make_user(1, "Admin", "User", assign_only_non_production_pets=True),
        make_user(2, "Regular", "User", assign_only_non_production_pets=True),
    ]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "misc01.example.com",
            "misc02.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        pool_name="non_production",
    ).generate()

    assert any("Assign ONLY Non-Production Pets" in warning for warning in result.warnings)
    assert [item.fqdn for item in assigned_items(result, 1)] == ["pet01.example.com"]
    assert assigned_items(result, 2) == []
    assert sorted(result.remaining_unassigned_hosts) == ["misc01.example.com", "misc02.example.com"]


def test_jboss_special_group_does_not_assign_any_host_twice():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        PRODUCTION_JBOSS_HOSTS
        + [
            "apisix-docker01-prod-bry.platform.is",
            "apisix-docker02-prod-bry.platform.is",
            "apisix-docker03-prod-bry.platform.is",
        ],
        seed=67,
        pool_name="production",
    ).generate()

    assigned_fqdns = [item.fqdn for _, item in flatten_assignments(result)]
    assert len(assigned_fqdns) == len(set(assigned_fqdns))


def test_non_contiguous_sequences_split_and_singletons_fall_back_to_random():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "kafka01-stage-bry.platform.is",
            "kafka02-stage-bry.platform.is",
            "kafka04-stage-bry.platform.is",
            "solo01-stage-bry.platform.is",
        ],
        seed=19,
    ).generate()

    grouped_sources = {group["source_name"] for group in result.grouped_prefix_sequences}
    assert "kafka-stage-bry.platform.is[01-02]" in grouped_sources
    assert all("kafka04-stage-bry.platform.is" not in group["source_name"] for group in result.grouped_prefix_sequences)
    assert any(item.fqdn == "kafka04-stage-bry.platform.is" and item.source_type == "random" for items in result.assignments_by_user.values() for item in items)
    assert any(item.fqdn == "solo01-stage-bry.platform.is" and item.source_type == "random" for items in result.assignments_by_user.values() for item in items)


def test_random_hosts_are_assigned_to_least_loaded_users():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "misc-a.example.com",
            "misc-b.example.com",
            "misc-c.example.com",
            "misc-d.example.com",
            "misc-e.example.com",
        ],
        seed=4,
    ).generate()

    counts = sorted(len(items) for items in result.assignments_by_user.values())
    assert counts == [2, 3]
    assert all(item.source_type == "random" for items in result.assignments_by_user.values() for item in items)


def test_generated_assignments_use_only_expected_source_types():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "kafka01-stage-bry.platform.is",
            "kafka02-stage-bry.platform.is",
            "misc-a.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        seed=21,
    ).generate()

    source_types = {
        item.source_type
        for items in result.assignments_by_user.values()
        for item in items
    }
    assert source_types <= {"pet", "prefix_sequence", "random"}
    assert "host_collection" not in source_types


def test_deterministic_output_when_seed_is_set():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    data = [
        "pet01.example.com",
        "db01.example.com",
        "db02.example.com",
        "misc-a.example.com",
        "misc-b.example.com",
        "misc-c.example.com",
    ]
    kwargs = {
        "pet_map": {1: {"pet01.example.com"}},
        "seed": 1234,
    }
    first = build_engine(users, data, **kwargs).generate()
    second = build_engine(users, data, **kwargs).generate()

    assert {
        user_id: [(item.fqdn, item.source_type, item.source_name) for item in items]
        for user_id, items in first.assignments_by_user.items()
    } == {
        user_id: [(item.fqdn, item.source_type, item.source_name) for item in items]
        for user_id, items in second.assignments_by_user.items()
    }
    assert first.warnings == second.warnings


def test_balance_is_as_small_as_practical_with_unsplittable_groups():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "pet01.example.com",
            "db01.example.com",
            "db02.example.com",
            "db03.example.com",
            "rand01.example.com",
            "rand02.example.com",
        ],
        pet_map={1: {"pet01.example.com"}},
        seed=13,
    ).generate()

    counts = sorted(len(items) for items in result.assignments_by_user.values())
    assert counts[1] - counts[0] <= 1


def test_prefix_sequence_groups_are_shuffled_before_assignment(monkeypatch):
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    rng = ReverseShuffleRandom()

    def fake_group_details(hosts, min_prefix_group_size=2):
        return [
            PrefixSequenceGroupDetail(
                group_key="alpha.example.com",
                hosts=["alpha01.example.com", "alpha02.example.com"],
                sequence_numbers=[1, 2],
                token_index=0,
                source_name="alpha.example.com[01-02]",
            ),
            PrefixSequenceGroupDetail(
                group_key="beta.example.com",
                hosts=["beta01.example.com", "beta02.example.com"],
                sequence_numbers=[1, 2],
                token_index=0,
                source_name="beta.example.com[01-02]",
            ),
        ]

    monkeypatch.setattr("app.services.assignment_engine.build_prefix_sequence_group_details", fake_group_details)

    result = AssignmentEngine(
        users=users,
        all_hosts=[
            "alpha01.example.com",
            "alpha02.example.com",
            "beta01.example.com",
            "beta02.example.com",
        ],
        pet_map={},
        config={
            "random_seed": None,
            "min_prefix_group_size": 2,
            "prefix_group_randomness_window": 0,
        },
        rng=rng,
    ).generate()

    assert [group["source_name"] for group in result.grouped_prefix_sequences] == [
        "beta.example.com[01-02]",
        "alpha.example.com[01-02]",
    ]


def test_prefix_group_randomness_window_zero_is_strict_least_loaded():
    rng = ReverseShuffleRandom()
    loads = {1: 0, 2: 1, 3: 1}

    assert _pick_prefix_group_user(loads, rng, 0) == 1
    assert rng.choice_inputs[0] == [1]


def test_prefix_group_randomness_window_one_allows_near_minimum_users():
    rng = ReverseShuffleRandom()
    loads = {1: 3, 2: 4, 3: 6}

    assert _pick_prefix_group_user(loads, rng, 1) == 2
    assert rng.choice_inputs[0] == [1, 2]


def test_prefix_sequence_groups_remain_unsplit_with_randomness_window():
    users = [make_user(1, "Admin", "User"), make_user(2, "Regular", "User")]
    result = build_engine(
        users,
        [
            "app01-worker01-prod-bry.platform.is",
            "app01-worker02-prod-bry.platform.is",
            "app01-worker03-prod-bry.platform.is",
            "misc01.example.com",
        ],
        seed=29,
        prefix_group_randomness_window=1,
    ).generate()

    prefix_assignments = {
        item.fqdn: user_id
        for user_id, items in result.assignments_by_user.items()
        for item in items
        if item.source_type == "prefix_sequence"
    }
    assert len(set(prefix_assignments.values())) == 1
