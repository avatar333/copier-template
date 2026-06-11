from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass


NUMBERED_SUFFIX_RE = re.compile(r"^(?P<prefix>.*?)(?P<number>\d{2})$")
FQDNISH_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def parse_pet_lines(raw_pets: str | None) -> list[str]:
    return normalize_fqdn_list(raw_pets)


def normalize_fqdn_list(raw_values: str | None) -> list[str]:
    if not raw_values:
        return []

    seen = set()
    values = []
    for line in raw_values.splitlines():
        fqdn = line.strip().lower()
        if not fqdn:
            continue
        if not FQDNISH_RE.match(fqdn):
            raise ValueError(f"Invalid FQDN value: {fqdn}")
        if fqdn not in seen:
            values.append(fqdn)
            seen.add(fqdn)
    return values


def parse_unique_fqdn_lines(raw_values: str | None) -> tuple[list[str], list[str]]:
    """Parse and normalize newline-delimited FQDN values.

    Returns the normalized values that passed validation together with a list of
    validation errors. Duplicate values are treated as errors but the unique
    normalized values already seen are preserved so the UI can be repopulated.
    """
    if not raw_values:
        return [], []

    seen = set()
    values: list[str] = []
    errors: list[str] = []
    for line in raw_values.splitlines():
        fqdn = line.strip().lower()
        if not fqdn:
            continue
        if not FQDNISH_RE.match(fqdn):
            errors.append(f"Invalid FQDN value: {fqdn}")
            continue
        if fqdn in seen:
            errors.append(f"Duplicate pet FQDNs are not allowed: {fqdn}")
            continue
        values.append(fqdn)
        seen.add(fqdn)
    return values, errors


@dataclass(slots=True)
class HostSequenceGroup:
    group_key: str
    hosts: list[str]


@dataclass(slots=True)
class PrefixSequenceMatch:
    fqdn: str
    group_key: str
    sequence_number: int
    token_index: int


@dataclass(slots=True)
class PrefixSequenceGroupDetail:
    group_key: str
    hosts: list[str]
    sequence_numbers: list[int]
    token_index: int
    source_name: str


@dataclass(slots=True)
class PrefixSequenceChoice:
    fqdn: str
    group_key: str
    sequence_number: int
    token_index: int
    run_length: int


def build_prefix_sequence_groups(
    hosts: list[str],
    min_prefix_group_size: int = 2,
) -> list[HostSequenceGroup]:
    return [
        HostSequenceGroup(group_key=group.group_key, hosts=group.hosts)
        for group in build_prefix_sequence_group_details(hosts, min_prefix_group_size=min_prefix_group_size)
    ]


def build_prefix_sequence_group_details(
    hosts: list[str],
    min_prefix_group_size: int = 2,
) -> list[PrefixSequenceGroupDetail]:
    """Group hosts by the strongest numeric-suffix token they share."""
    choices = build_prefix_sequence_candidate_choices(hosts)
    if not choices:
        return []

    chosen_matches_by_key: dict[str, list[PrefixSequenceMatch]] = defaultdict(list)
    for choice in choices:
        chosen_matches_by_key[choice.group_key].append(
            PrefixSequenceMatch(
                fqdn=choice.fqdn,
                group_key=choice.group_key,
                sequence_number=choice.sequence_number,
                token_index=choice.token_index,
            )
        )

    grouped: list[PrefixSequenceGroupDetail] = []
    for group_key, matches in chosen_matches_by_key.items():
        matches.sort(key=lambda match: (match.sequence_number, match.fqdn))
        for run in _iter_contiguous_runs(matches):
            if len(run) < min_prefix_group_size:
                continue
            hosts_in_run = [match.fqdn for match in run]
            sequence_numbers = [match.sequence_number for match in run]
            grouped.append(
                PrefixSequenceGroupDetail(
                    group_key=group_key,
                    hosts=hosts_in_run,
                    sequence_numbers=sequence_numbers,
                    token_index=min(match.token_index for match in run),
                    source_name=_build_source_name(group_key, sequence_numbers),
                )
            )

    return grouped


def build_prefix_sequence_candidate_choices(hosts: list[str]) -> list[PrefixSequenceChoice]:
    normalized_hosts = sorted({fqdn.lower() for fqdn in hosts if fqdn})
    if not normalized_hosts:
        return []

    matches_by_key: dict[str, list[PrefixSequenceMatch]] = defaultdict(list)
    matches_by_host: dict[str, list[PrefixSequenceMatch]] = defaultdict(list)
    for fqdn in normalized_hosts:
        for match in _extract_prefix_sequence_matches(fqdn):
            matches_by_key[match.group_key].append(match)
            matches_by_host[fqdn].append(match)

    if not matches_by_key:
        return []

    score_by_host_key: dict[tuple[str, str], tuple[int, int, str]] = {}
    for group_key, matches in matches_by_key.items():
        matches.sort(key=lambda match: (match.sequence_number, match.fqdn))
        for run in _iter_contiguous_runs(matches):
            run_length = len(run)
            for match in run:
                score_by_host_key[(match.fqdn, group_key)] = (
                    run_length,
                    -match.token_index,
                    group_key,
                )

    choices: list[PrefixSequenceChoice] = []
    for fqdn, matches in matches_by_host.items():
        best_match = max(matches, key=lambda match: score_by_host_key[(fqdn, match.group_key)])
        run_length = score_by_host_key[(fqdn, best_match.group_key)][0]
        choices.append(
            PrefixSequenceChoice(
                fqdn=fqdn,
                group_key=best_match.group_key,
                sequence_number=best_match.sequence_number,
                token_index=best_match.token_index,
                run_length=run_length,
            )
        )

    return choices


def least_loaded_user_id(loads: dict[int, int], rng: random.Random) -> int:
    lowest = min(loads.values())
    candidates = [user_id for user_id, load in loads.items() if load == lowest]
    return rng.choice(candidates)


def _build_source_name(group_key: str, sequence_numbers: list[int]) -> str:
    numbers = sequence_numbers
    if not numbers:
        return group_key
    start = min(numbers)
    end = max(numbers)
    if start == end:
        return f"{group_key}[{start:02d}]"
    return f"{group_key}[{start:02d}-{end:02d}]"


def _extract_prefix_sequence_matches(fqdn: str) -> list[PrefixSequenceMatch]:
    parts = fqdn.lower().split(".", 1)
    if len(parts) != 2:
        return []

    host_label, domain = parts
    tokens = host_label.split("-")
    if not tokens:
        return []

    matches: list[PrefixSequenceMatch] = []
    for token_index, token in enumerate(tokens):
        match = NUMBERED_SUFFIX_RE.match(token)
        if not match:
            continue
        prefix = match.group("prefix")
        if not prefix:
            continue
        number = int(match.group("number"))
        normalized_tokens = list(tokens)
        normalized_tokens[token_index] = prefix
        group_key = f"{'-'.join(normalized_tokens)}.{domain}"
        matches.append(
            PrefixSequenceMatch(
                fqdn=fqdn.lower(),
                group_key=group_key,
                sequence_number=number,
                token_index=token_index,
            )
        )
    return matches


def _iter_contiguous_runs(matches: list[PrefixSequenceMatch]) -> list[list[PrefixSequenceMatch]]:
    runs: list[list[PrefixSequenceMatch]] = []
    run: list[PrefixSequenceMatch] = []
    for match in matches:
        if not run or match.sequence_number == run[-1].sequence_number + 1:
            run.append(match)
            continue
        runs.append(run)
        run = [match]
    if run:
        runs.append(run)
    return runs
