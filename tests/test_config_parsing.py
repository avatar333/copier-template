from __future__ import annotations

from pathlib import Path

from app.config import build_config_dict


def test_build_config_from_yaml_like_db_details_and_pat(tmp_path: Path):
    db_details_path = tmp_path / "db_details.txt"
    db_details_path.write_text(
        "\n".join(
            [
                "VIP: db.example.internal",
                "db_name: forekat",
                "username: forekat_user",
                "password: hidden",
            ]
        )
    )
    pat_path = tmp_path / "pat.txt"
    pat_path.write_text(
        "\n".join(
            [
                "username: foreman-user",
                "PAT_token: token-value",
            ]
        )
    )

    config = build_config_dict(db_details_path=db_details_path, pat_path=pat_path)

    assert config["database"]["host"] == "db.example.internal"
    assert config["database"]["name"] == "forekat"
    assert config["database"]["username"] == "forekat_user"
    assert config["forekat"]["username"] == "foreman-user"
    assert config["forekat"]["personal_access_token"] == "token-value"
    assert config["database"]["sqlalchemy_uri"].startswith("mysql+pymysql://")
    assert config["assignment"]["prefix_group_randomness_window"] == 1


def test_build_config_from_uri_and_pat_only(tmp_path: Path):
    db_details_path = tmp_path / "db_details.txt"
    db_details_path.write_text("mysql+pymysql://user:password@db.internal:3307/forekat")
    pat_path = tmp_path / "pat.txt"
    pat_path.write_text("token-value")

    config = build_config_dict(db_details_path=db_details_path, pat_path=pat_path)

    assert config["database"]["host"] == "db.internal"
    assert config["database"]["port"] == 3307
    assert config["database"]["name"] == "forekat"
    assert config["forekat"]["username"] == "TODO_FOREMAN_USERNAME"
    assert config["forekat"]["personal_access_token"] == "token-value"
    assert config["assignment"]["prefix_group_randomness_window"] == 1
