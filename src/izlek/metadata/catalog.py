"""Static catalog of metadata sources and what each can provide."""

from dataclasses import dataclass
from enum import StrEnum

from izlek.metadata.capabilities import Capability


class SourceId(StrEnum):
    TMDB = "tmdb"
    TRAKT = "trakt"
    TVMAZE = "tvmaze"
    OMDB = "omdb"


class CommercialPolicy(StrEnum):
    """How the source may be used relative to İzlek's distribution."""

    OK = "ok"
    NON_COMMERCIAL_ONLY = "non_commercial_only"
    ATTRIBUTION_REQUIRED = "attribution_required"


class CredentialKind(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    CLIENT_ID = "client_id"
    API_KEY = "api_key"


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    id: SourceId
    label: str
    summary: str
    supported: frozenset[Capability]
    default_enabled: bool
    default_capabilities: frozenset[Capability]
    credential_kind: CredentialKind
    commercial_policy: CommercialPolicy
    credential_label: str
    notes: str


SOURCE_CATALOG: dict[SourceId, SourceDefinition] = {
    SourceId.TMDB: SourceDefinition(
        id=SourceId.TMDB,
        label="TMDb",
        summary=(
            "Varsayılan katalog: arama, keşfet, detay, görseller ve "
            "JustWatch sağlayıcıları."
        ),
        supported=frozenset(
            {
                Capability.SEARCH,
                Capability.DISCOVER,
                Capability.DETAILS,
                Capability.SEASONS,
                Capability.PEOPLE,
                Capability.IMAGES,
                Capability.VIDEOS,
                Capability.WATCH_PROVIDERS,
            }
        ),
        default_enabled=True,
        default_capabilities=frozenset(
            {
                Capability.SEARCH,
                Capability.DISCOVER,
                Capability.DETAILS,
                Capability.SEASONS,
                Capability.PEOPLE,
                Capability.IMAGES,
                Capability.VIDEOS,
                Capability.WATCH_PROVIDERS,
            }
        ),
        credential_kind=CredentialKind.BEARER,
        commercial_policy=CommercialPolicy.OK,
        credential_label="API Read Access Token",
        notes=(
            "Ticari kullanım için TMDB iş anlaşması gerekebilir; "
            "kişisel takip için uygundur."
        ),
    ),
    SourceId.TRAKT: SourceDefinition(
        id=SourceId.TRAKT,
        label="Trakt",
        summary=(
            "Film/dizi kataloğu, arama ve bölüm metadata'sı; "
            "görsel/CDN için TMDb gerekir."
        ),
        supported=frozenset(
            {
                Capability.SEARCH,
                Capability.DETAILS,
                Capability.SEASONS,
                Capability.PEOPLE,
            }
        ),
        default_enabled=False,
        default_capabilities=frozenset(
            {
                Capability.SEARCH,
                Capability.DETAILS,
                Capability.SEASONS,
            }
        ),
        credential_kind=CredentialKind.CLIENT_ID,
        commercial_policy=CommercialPolicy.OK,
        credential_label="Trakt Client ID",
        notes="Standart API ticari kullanıma açıktır; watchnow uçları sınırlıdır.",
    ),
    SourceId.TVMAZE: SourceDefinition(
        id=SourceId.TVMAZE,
        label="TVmaze",
        summary="Yalnız dizi: gösterim, bölüm ve yayın takvimi. Film katmanı yoktur.",
        supported=frozenset(
            {
                Capability.SEARCH,
                Capability.DETAILS,
                Capability.SEASONS,
                Capability.PEOPLE,
            }
        ),
        default_enabled=False,
        default_capabilities=frozenset(
            {
                Capability.SEARCH,
                Capability.DETAILS,
                Capability.SEASONS,
            }
        ),
        credential_kind=CredentialKind.NONE,
        commercial_policy=CommercialPolicy.ATTRIBUTION_REQUIRED,
        credential_label="",
        notes="Ücretsiz katman CC BY-SA atıf ister; film metadata'sı sağlamaz.",
    ),
    SourceId.OMDB: SourceDefinition(
        id=SourceId.OMDB,
        label="OMDb",
        summary="İnce IMDb tarzı başlık bakışı; Keşfet/sezon/sağlayıcı yerine geçmez.",
        supported=frozenset({Capability.TITLE_LOOKUP}),
        default_enabled=False,
        default_capabilities=frozenset({Capability.TITLE_LOOKUP}),
        credential_kind=CredentialKind.API_KEY,
        commercial_policy=CommercialPolicy.NON_COMMERCIAL_ONLY,
        credential_label="OMDb API Key",
        notes=(
            "Kişisel / ticari olmayan kullanımla sınırlıdır. "
            "Etkinleştirmek için Ayarlar'da ticari olmama onayını işaretleyin."
        ),
    ),
}


WATCH_PROVIDER_REGIONS: tuple[tuple[str, str], ...] = (
    ("TR", "Türkiye"),
    ("US", "ABD"),
    ("GB", "Birleşik Krallık"),
    ("DE", "Almanya"),
    ("FR", "Fransa"),
    ("KR", "Güney Kore"),
    ("JP", "Japonya"),
    ("CA", "Kanada"),
    ("AU", "Avustralya"),
    ("BR", "Brezilya"),
    ("ES", "İspanya"),
    ("IT", "İtalya"),
    ("NL", "Hollanda"),
    ("SE", "İsveç"),
    ("PL", "Polonya"),
    ("IN", "Hindistan"),
)

DEFAULT_WATCH_PROVIDER_REGION = "TR"
_ALLOWED_REGIONS = frozenset(code for code, _ in WATCH_PROVIDER_REGIONS)


def normalize_watch_region(code: str | None) -> str:
    """Return a supported ISO region or the TR default."""
    candidate = (code or "").strip().upper()
    if candidate in _ALLOWED_REGIONS:
        return candidate
    return DEFAULT_WATCH_PROVIDER_REGION
