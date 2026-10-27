"""Optional OMDb / Trakt enrichment for detail presentation."""

from __future__ import annotations

from typing import Any

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SourceId
from izlek.metadata.clients import OmdbMetadataClient, TraktMetadataClient
from izlek.metadata.protocol import UnsupportedCapabilityError
from izlek.metadata.registry import MetadataClientRegistry
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError


def enrich_detail(
    presentation: dict[str, Any],
    *,
    media_type: str,
    tmdb_id: int,
    client: TmdbClient,
    registry: MetadataClientRegistry | None,
    title: str = "",
    year: str = "",
) -> dict[str, Any]:
    """Attach IMDb (OMDb) and Trakt scores when those sources are live-enabled.

    Failures are swallowed so TMDb detail remains usable offline / without keys.
    """
    if registry is None:
        return presentation
    result = dict(presentation)
    imdb_id = ""
    try:
        if media_type == "movie":
            external = client.movie_external_ids(tmdb_id)
        else:
            external = client.tv_external_ids(tmdb_id)
        imdb_id = (external.imdb_id or "").strip()
    except (TMDbError, NetworkError, OSError, ValueError):
        imdb_id = ""
    if imdb_id:
        result["imdbId"] = imdb_id

    try:
        omdb = registry.resolve(Capability.TITLE_LOOKUP)
    except UnsupportedCapabilityError:
        omdb = None
    if isinstance(omdb, OmdbMetadataClient):
        try:
            lookup = omdb.title_lookup(
                imdb_id=imdb_id, title=title if not imdb_id else "", year=year
            )
            rating = lookup.get("imdbRating") or ""
            if rating and rating != "N/A":
                result["imdbRating"] = rating
                result["imdbVotes"] = lookup.get("imdbVotes") or ""
                result["imdbId"] = lookup.get("imdbId") or imdb_id
        except UnsupportedCapabilityError:
            pass

    try:
        for candidate in registry.candidates(Capability.DETAILS):
            if isinstance(candidate, TraktMetadataClient) and candidate.supports(
                Capability.DETAILS
            ):
                trakt = candidate.details_by_tmdb(
                    media_type=media_type, tmdb_id=tmdb_id
                )
                if trakt:
                    if trakt.get("score"):
                        result["traktRating"] = round(float(trakt["score"]), 1)
                    if trakt.get("votes"):
                        result["traktVotes"] = int(trakt["votes"])
                    if trakt.get("imdbId") and not result.get("imdbId"):
                        result["imdbId"] = trakt["imdbId"]
                break
    except (UnsupportedCapabilityError, OSError, ValueError, TypeError):
        pass
    return result
