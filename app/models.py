from pydantic import BaseModel


class ArtistInfo(BaseModel):
    artist: str
    genre: str
    content_score: float | None = None
    image_url: str | None = None
    spotify_id: str | None = None


class RecommendationResponse(BaseModel):
    recommendations: list[ArtistInfo]
    method: str
