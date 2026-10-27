"""App-facing metadata capabilities İzlek actually needs."""

from enum import StrEnum


class Capability(StrEnum):
    """Coarse features that map to Settings toggles and client methods."""

    SEARCH = "search"
    DISCOVER = "discover"
    DETAILS = "details"
    SEASONS = "seasons"
    PEOPLE = "people"
    IMAGES = "images"
    VIDEOS = "videos"
    WATCH_PROVIDERS = "watch_providers"
    TITLE_LOOKUP = "title_lookup"


CAPABILITY_LABELS: dict[Capability, str] = {
    Capability.SEARCH: "Arama",
    Capability.DISCOVER: "Keşfet",
    Capability.DETAILS: "Detay",
    Capability.SEASONS: "Sezon / bölüm",
    Capability.PEOPLE: "Kişi / yönetmen",
    Capability.IMAGES: "Görseller",
    Capability.VIDEOS: "Fragman",
    Capability.WATCH_PROVIDERS: "Nerede izlenir",
    Capability.TITLE_LOOKUP: "Başlık zenginleştirme",
}


CAPABILITY_DESCRIPTIONS: dict[Capability, str] = {
    Capability.SEARCH: "Film ve dizi adı araması",
    Capability.DISCOVER: "Keşfet filtreleri ve popüler listeler",
    Capability.DETAILS: "Başlık, özet, puan ve temel metadata",
    Capability.SEASONS: "Dizi sezon ve bölüm listeleri",
    Capability.PEOPLE: "Oyuncu/yönetmen araması ve krediler",
    Capability.IMAGES: "Poster, backdrop ve profil görselleri",
    Capability.VIDEOS: "Fragman ve video bağlantıları",
    Capability.WATCH_PROVIDERS: "Bölgesel izleme sağlayıcıları",
    Capability.TITLE_LOOKUP: "IMDb kimliği / ince başlık bilgisi",
}
