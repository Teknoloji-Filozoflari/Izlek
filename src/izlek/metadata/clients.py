"""Concrete metadata clients: TMDb adapter plus capability-gated supplements."""

from __future__ import annotations

from typing import Any

import httpx

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SOURCE_CATALOG, SourceId
from izlek.metadata.protocol import UnsupportedCapabilityError
from izlek.tmdb.client import TmdbClient

_OMDB_URL = "https://www.omdbapi.com/"
_TRAKT_URL = "https://api.trakt.tv"
_HTTP_TIMEOUT = 8.0


class BaseMetadataClient:
    """Shared capability helpers for catalog-backed clients."""

    source_id: SourceId

    def supported_capabilities(self) -> frozenset[Capability]:
        return SOURCE_CATALOG[self.source_id].supported

    def implemented_capabilities(self) -> frozenset[Capability]:
        return frozenset()

    def supports(self, capability: Capability) -> bool:
        return capability in self.implemented_capabilities()

    def require(self, capability: Capability) -> None:
        if not self.supports(capability):
            label = SOURCE_CATALOG[self.source_id].label
            raise UnsupportedCapabilityError(
                f"{label} şu anda {capability.value} yeteneğini uygulamıyor."
            )


class TmdbMetadataClient(BaseMetadataClient):
    """Adapt the existing TMDb HTTP client to the shared metadata interface."""

    source_id = SourceId.TMDB

    def __init__(self, client: TmdbClient | None = None) -> None:
        self.client = client or TmdbClient()

    def implemented_capabilities(self) -> frozenset[Capability]:
        return self.supported_capabilities()

    def __getattr__(self, name: str):
        return getattr(self.client, name)


class TraktMetadataClient(BaseMetadataClient):
    """Live Trakt search/details using the stored Client ID (API key header)."""

    source_id = SourceId.TRAKT

    def __init__(
        self,
        client_id: str | None = None,
        *,
        http: httpx.Client | None = None,
    ) -> None:
        self.client_id = (client_id or "").strip() or None
        self._http = http

    def implemented_capabilities(self) -> frozenset[Capability]:
        if self.client_id:
            return frozenset({Capability.SEARCH, Capability.DETAILS})
        return frozenset()

    def _client(self) -> httpx.Client:
        if self._http is not None:
            return self._http
        return httpx.Client(timeout=_HTTP_TIMEOUT)

    def _headers(self) -> dict[str, str]:
        if not self.client_id:
            raise UnsupportedCapabilityError("Trakt Client ID gerekli.")
        return {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": self.client_id,
        }

    def search(
        self, query: str, *, types: tuple[str, ...] = ("movie", "show")
    ) -> list[dict[str, Any]]:
        """Search Trakt titles; returns normalized rows with TMDb ids when present."""
        self.require(Capability.SEARCH)
        q = query.strip()
        if len(q) < 2:
            return []
        type_path = ",".join(types)
        owns = self._http is None
        client = self._client()
        try:
            response = client.get(
                f"{_TRAKT_URL}/search/{type_path}",
                params={"query": q, "extended": "full"},
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UnsupportedCapabilityError(f"Trakt araması başarısız: {exc}") from exc
        finally:
            if owns:
                client.close()
        rows: list[dict[str, Any]] = []
        if not isinstance(payload, list):
            return rows
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            kind = str(entry.get("type") or "")
            body = entry.get(kind) if kind in {"movie", "show"} else None
            if not isinstance(body, dict):
                continue
            ids = body.get("ids") if isinstance(body.get("ids"), dict) else {}
            title = str(body.get("title") or "")
            year = body.get("year")
            rows.append(
                {
                    "source": "trakt",
                    "mediaType": "movie" if kind == "movie" else "tv",
                    "title": title,
                    "year": str(year) if year else "",
                    "traktId": ids.get("trakt"),
                    "tmdbId": ids.get("tmdb"),
                    "imdbId": ids.get("imdb") or "",
                    "slug": ids.get("slug") or "",
                    "score": float(body.get("rating") or 0),
                    "votes": int(body.get("votes") or 0),
                    "overview": str(body.get("overview") or ""),
                }
            )
        return rows

    def details(self, *, media_type: str, trakt_id: int) -> dict[str, Any]:
        """Fetch one Trakt movie/show detail by Trakt id."""
        self.require(Capability.DETAILS)
        kind = "movies" if media_type == "movie" else "shows"
        owns = self._http is None
        client = self._client()
        try:
            response = client.get(
                f"{_TRAKT_URL}/{kind}/{int(trakt_id)}",
                params={"extended": "full"},
                headers=self._headers(),
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UnsupportedCapabilityError(f"Trakt detayı başarısız: {exc}") from exc
        finally:
            if owns:
                client.close()
        if not isinstance(body, dict):
            raise UnsupportedCapabilityError("Trakt geçersiz yanıt döndü.")
        ids = body.get("ids") if isinstance(body.get("ids"), dict) else {}
        return {
            "source": "trakt",
            "mediaType": media_type,
            "title": str(body.get("title") or ""),
            "year": str(body.get("year") or ""),
            "traktId": ids.get("trakt"),
            "tmdbId": ids.get("tmdb"),
            "imdbId": ids.get("imdb") or "",
            "slug": ids.get("slug") or "",
            "score": float(body.get("rating") or 0),
            "votes": int(body.get("votes") or 0),
            "overview": str(body.get("overview") or ""),
        }

    def details_by_tmdb(
        self, *, media_type: str, tmdb_id: int
    ) -> dict[str, Any] | None:
        """Resolve Trakt detail via TMDb id search (best-effort enrichment)."""
        self.require(Capability.DETAILS)
        kind = "movie" if media_type == "movie" else "show"
        owns = self._http is None
        client = self._client()
        try:
            response = client.get(
                f"{_TRAKT_URL}/search/tmdb/{int(tmdb_id)}",
                params={"type": kind},
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        finally:
            if owns:
                client.close()
        if not isinstance(payload, list) or not payload:
            return None
        first = payload[0]
        if not isinstance(first, dict):
            return None
        body = first.get(kind)
        if not isinstance(body, dict):
            return None
        ids = body.get("ids") if isinstance(body.get("ids"), dict) else {}
        trakt_id = ids.get("trakt")
        if not trakt_id:
            return None
        try:
            return self.details(media_type=media_type, trakt_id=int(trakt_id))
        except UnsupportedCapabilityError:
            return None


class TvmazeMetadataClient(BaseMetadataClient):
    """TVmaze wiring for TV-only capabilities; HTTP fetch lands later."""

    source_id = SourceId.TVMAZE


class OmdbMetadataClient(BaseMetadataClient):
    """Live OMDb title lookup gated to non-commercial acknowledgment + API key."""

    source_id = SourceId.OMDB

    def __init__(
        self,
        api_key: str | None = None,
        *,
        non_commercial_acknowledged: bool = False,
        http: httpx.Client | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip() or None
        self.non_commercial_acknowledged = non_commercial_acknowledged
        self._http = http

    def implemented_capabilities(self) -> frozenset[Capability]:
        if self.non_commercial_acknowledged and self.api_key:
            return frozenset({Capability.TITLE_LOOKUP})
        return frozenset()

    def _client(self) -> httpx.Client:
        if self._http is not None:
            return self._http
        return httpx.Client(timeout=_HTTP_TIMEOUT)

    def title_lookup(
        self, *, imdb_id: str = "", title: str = "", year: str = ""
    ) -> dict[str, str]:
        """Fetch IMDb-style fields from OMDb (personal / non-commercial only)."""
        self.require(Capability.TITLE_LOOKUP)
        if not imdb_id and not title:
            raise UnsupportedCapabilityError("OMDb için imdb_id veya title gerekli.")
        params: dict[str, str] = {"apikey": self.api_key or ""}
        if imdb_id:
            params["i"] = imdb_id.strip()
        else:
            params["t"] = title.strip()
            if year:
                params["y"] = year.strip()
        owns = self._http is None
        client = self._client()
        try:
            response = client.get(_OMDB_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UnsupportedCapabilityError(f"OMDb isteği başarısız: {exc}") from exc
        finally:
            if owns:
                client.close()
        if not isinstance(data, dict) or data.get("Response") == "False":
            message = ""
            if isinstance(data, dict):
                message = str(data.get("Error") or "")
            raise UnsupportedCapabilityError(message or "OMDb kayıt bulamadı.")
        return {
            "imdbId": str(data.get("imdbID") or ""),
            "imdbRating": str(data.get("imdbRating") or ""),
            "imdbVotes": str(data.get("imdbVotes") or ""),
            "title": str(data.get("Title") or ""),
            "year": str(data.get("Year") or ""),
            "plot": str(data.get("Plot") or ""),
            "rated": str(data.get("Rated") or ""),
            "source": "omdb",
        }


def build_supplement_clients(
    *,
    trakt_client_id: str | None = None,
    omdb_api_key: str | None = None,
    omdb_acknowledged: bool = False,
) -> dict[SourceId, BaseMetadataClient]:
    """Construct non-TMDb clients from stored credentials and ToS state."""
    return {
        SourceId.TRAKT: TraktMetadataClient(trakt_client_id),
        SourceId.TVMAZE: TvmazeMetadataClient(),
        SourceId.OMDB: OmdbMetadataClient(
            omdb_api_key, non_commercial_acknowledged=omdb_acknowledged
        ),
    }
