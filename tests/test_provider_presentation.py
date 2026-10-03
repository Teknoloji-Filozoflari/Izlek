from izlek.services.provider_presentation import present_providers


def test_provider_groups_keep_supported_watch_modes_and_tmdb_link():
    groups, link = present_providers(
        {
            "link": "https://www.themoviedb.org/movie/42/watch?locale=TR",
            "flatrate": [{"provider_name": "Stream"}],
            "free": [{"provider_name": "Free"}],
            "ads": [{"provider_name": "Ads"}],
            "rent": [{"provider_name": "Rent"}],
            "buy": [{"provider_name": "Buy"}],
        }
    )

    assert groups == {
        "Abonelik": ["Stream"],
        "Kiralama": ["Rent"],
        "Satın Alma": ["Buy"],
    }
    assert link.endswith("locale=TR")


def test_provider_presentation_hides_unsafe_link_and_handles_empty_region():
    groups, link = present_providers(
        {"link": "https://example.invalid/watch", "rent": [{"provider_name": ""}]}
    )

    assert groups == {"Abonelik": [], "Kiralama": [], "Satın Alma": []}
    assert link == ""
