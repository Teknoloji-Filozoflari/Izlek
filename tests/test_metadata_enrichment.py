"""Live OMDb / Trakt enrichment for detail presentation."""

import httpx

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SourceId
from izlek.metadata.clients import (
    OmdbMetadataClient,
    TraktMetadataClient,
    build_supplement_clients,
)
from izlek.metadata.protocol import UnsupportedCapabilityError
from izlek.services.metadata_enrichment import enrich_detail
from izlek.tmdb.models import ExternalIds


class _Tmdb:
    def movie_external_ids(self, movie_id: int) -> ExternalIds:
        return ExternalIds.model_validate({"imdb_id": "tt1375666", "id": movie_id})


class _Registry:
    def __init__(self, omdb=None, trakt=None) -> None:
        self._omdb = omdb
        self._trakt = trakt

    def resolve(self, capability):
        if capability is Capability.TITLE_LOOKUP and self._omdb is not None:
            return self._omdb
        raise UnsupportedCapabilityError("unsupported")

    def candidates(self, capability):
        if capability is Capability.DETAILS and self._trakt is not None:
            return [self._trakt]
        return []


def test_enrich_detail_attaches_imdb_and_trakt_scores():
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.omdbapi.com":
            return httpx.Response(
                200,
                json={
                    "Response": "True",
                    "imdbID": "tt1375666",
                    "imdbRating": "8.8",
                    "imdbVotes": "2,000,000",
                    "Title": "Inception",
                    "Year": "2010",
                    "Plot": "",
                    "Rated": "PG-13",
                },
            )
        if "/search/tmdb/" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "type": "movie",
                        "movie": {
                            "title": "Inception",
                            "ids": {"trakt": 1, "tmdb": 27205, "imdb": "tt1375666"},
                        },
                    }
                ],
            )
        if request.url.path.endswith("/movies/1"):
            return httpx.Response(
                200,
                json={
                    "title": "Inception",
                    "year": 2010,
                    "rating": 8.5,
                    "votes": 1000,
                    "overview": "",
                    "ids": {"trakt": 1, "tmdb": 27205, "imdb": "tt1375666"},
                },
            )
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        omdb = OmdbMetadataClient(
            "key", non_commercial_acknowledged=True, http=http
        )
        trakt = TraktMetadataClient("client-id", http=http)
        result = enrich_detail(
            {"title": "Inception", "year": "2010"},
            media_type="movie",
            tmdb_id=27205,
            client=_Tmdb(),
            registry=_Registry(omdb=omdb, trakt=trakt),
            title="Inception",
            year="2010",
        )
    assert result["imdbId"] == "tt1375666"
    assert result["imdbRating"] == "8.8"
    assert result["traktRating"] == 8.5
    assert result["traktVotes"] == 1000


def test_build_supplement_clients_gate_omdb_without_ack():
    clients = build_supplement_clients(
        trakt_client_id="cid",
        omdb_api_key="key",
        omdb_acknowledged=False,
    )
    assert not clients[SourceId.OMDB].supports(Capability.TITLE_LOOKUP)
    assert clients[SourceId.TRAKT].supports(Capability.DETAILS)


def test_enrich_detail_noop_without_registry():
    base = {"title": "X", "score": 7}
    assert enrich_detail(
        base,
        media_type="movie",
        tmdb_id=1,
        client=_Tmdb(),
        registry=None,
    ) == base
