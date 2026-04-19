from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecommendationRequest:
    face_shape: str
    hair_length: str
    style_goal: str
    maintenance_level: str
    beard_style: str
    has_selfie: bool


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    slug: str
    name: str
    summary: str
    score: int
    maintenance_level: str
    booking_service_name: str
    image_url: str
    match_reason: str


class RecommendationEngine:
    def recommend(
        self,
        request: RecommendationRequest,
        catalog: list[dict[str, str]],
        *,
        limit: int = 4,
    ) -> list[RecommendationResult]:
        results: list[RecommendationResult] = []

        for item in catalog:
            face_shapes = self._split_tags(item["face_shapes"])
            hair_lengths = self._split_tags(item["hair_lengths"])
            style_goals = self._split_tags(item["style_goals"])
            beard_styles = self._split_tags(item["beard_styles"])

            score = 0
            reasons: list[str] = []

            if request.face_shape != "Bilmayman" and request.face_shape in face_shapes:
                score += 4
                reasons.append(f"yuz shakli {request.face_shape.lower()} bilan yaxshi ishlaydi")
            if request.hair_length in hair_lengths:
                score += 3
                reasons.append(f"joriy uzunlik {request.hair_length.lower()} segmentiga mos")
            if request.style_goal in style_goals:
                score += 3
                reasons.append(f"siz xohlagan '{request.style_goal}' yo'nalishiga yaqin")
            if request.maintenance_level == item["maintenance_level"]:
                score += 2
                reasons.append(f"parvarish darajasi {request.maintenance_level.lower()}")
            if request.beard_style in beard_styles:
                score += 2
                reasons.append(f"{request.beard_style.lower()} bilan balans beradi")
            if request.has_selfie:
                score += 1

            if not reasons:
                reasons.append("universal va xavfsiz variant")

            results.append(
                RecommendationResult(
                    slug=item["slug"],
                    name=item["name"],
                    summary=item["summary"],
                    score=score,
                    maintenance_level=item["maintenance_level"],
                    booking_service_name=item["booking_service_name"],
                    image_url=item["reference_url"],
                    match_reason=self._compose_reason(reasons),
                )
            )

        results.sort(key=lambda item: (-item.score, item.name))
        return results[:limit]

    @staticmethod
    def _split_tags(raw_value: str) -> tuple[str, ...]:
        return tuple(part.strip() for part in raw_value.split(",") if part.strip())

    @staticmethod
    def _compose_reason(reasons: list[str]) -> str:
        if len(reasons) == 1:
            return reasons[0]
        if len(reasons) == 2:
            return f"{reasons[0]} va {reasons[1]}"
        return f"{reasons[0]}, {reasons[1]} va {reasons[2]}"
