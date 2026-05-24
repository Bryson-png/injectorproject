"""test_attacks.py — Verify the attack library is well-formed."""
from attacks import ATTACKS, get_attacks_for_scenario, get_all_families


REQUIRED_FIELDS = {"id", "family", "name", "scenarios", "description", "payload"}
EXPECTED_PER_SCENARIO = 7  # 4 universal + 3 scenario-specific
SCENARIOS = ["code_review", "legal_disclaimer", "brand_pr"]


def main():
    print(f"Total attacks in library: {len(ATTACKS)}")
    print(f"Attack families: {get_all_families()}\n")

    # Schema check
    for attack in ATTACKS:
        missing = REQUIRED_FIELDS - attack.keys()
        assert not missing, f"{attack.get('id', '?')} missing fields: {missing}"
        assert isinstance(attack["scenarios"], list), (
            f"{attack['id']} scenarios must be a list"
        )

    # Unique IDs
    ids = [a["id"] for a in ATTACKS]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {[i for i in ids if ids.count(i) > 1]}"

    # Per-scenario count
    for scenario in SCENARIOS:
        attacks = get_attacks_for_scenario(scenario)
        names = [a["name"] for a in attacks]
        print(f"  {scenario:20s}: {len(attacks)} attacks — {', '.join(a['id'] for a in attacks)}")
        assert len(attacks) == EXPECTED_PER_SCENARIO, (
            f"Scenario '{scenario}' expected {EXPECTED_PER_SCENARIO} attacks, got {len(attacks)}"
        )

    print("\nAll checks passed!")


if __name__ == "__main__":
    main()
