import pytest

from gemma_jev.media_policy import MediaPolicy, parse_allowed_media_domains


def test_remote_images_are_denied_by_default() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        MediaPolicy().validate_url("https://images.example.com/a.png")


def test_exact_allowlisted_hosts_are_accepted() -> None:
    policy = MediaPolicy(allowed_domains=("images.example.com",))

    policy.validate_url("https://images.example.com/a.png")
    policy.validate_url("http://images.example.com:8080/a.png")


def test_subdomains_are_not_implicitly_allowed() -> None:
    policy = MediaPolicy(allowed_domains=("example.com",))

    with pytest.raises(ValueError, match="not allowed"):
        policy.validate_url("https://images.example.com/a.png")


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/image.png",
        "ftp://images.example.com/a.png",
        "https://user:pass@images.example.com/a.png",
        "not-a-url",
    ],
)
def test_unsafe_or_malformed_urls_are_rejected(url: str) -> None:
    policy = MediaPolicy(allowed_domains=("images.example.com",))

    with pytest.raises(ValueError):
        policy.validate_url(url)


def test_data_urls_require_explicit_opt_in() -> None:
    url = "data:image/png;base64,AAAA"

    with pytest.raises(ValueError, match="disabled"):
        MediaPolicy().validate_url(url)

    MediaPolicy(allow_data_urls=True).validate_url(url)


def test_non_image_data_url_is_rejected_even_when_enabled() -> None:
    with pytest.raises(ValueError, match="only image"):
        MediaPolicy(allow_data_urls=True).validate_url("data:text/plain;base64,AAAA")


def test_domain_environment_parser_is_exact_and_deduplicated() -> None:
    assert parse_allowed_media_domains("Images.Example.com,cdn.example.com,images.example.com") == (
        "images.example.com",
        "cdn.example.com",
    )

    with pytest.raises(ValueError):
        parse_allowed_media_domains("https://images.example.com")
