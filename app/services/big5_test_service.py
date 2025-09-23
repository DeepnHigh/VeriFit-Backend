from sqlalchemy.orm import Session
from app.models.big5_test_result import Big5TestResult
from app.models.job_seeker import JobSeeker
from app.schemas.big5_test import Big5TestResultCreate
from typing import Optional
import uuid

class Big5TestService:
    def __init__(self, db: Session):
        self.db = db

    def get_big5_test_result(self, user_id: str) -> Optional[Big5TestResult]:
        """지원자 Big5 성격검사 결과 조회"""
        return self.db.query(Big5TestResult).filter(
            Big5TestResult.job_seeker_id == user_id
        ).first()

    def save_big5_result(self, data: Big5TestResultCreate) -> Big5TestResult:
        """JSON 바디로 전달된 Big5 결과를 저장하고 job_seekers.big5_text 업데이트"""
        db_big5 = Big5TestResult(**data.dict())
        self.db.add(db_big5)
        
        # big5_text 생성 로직: 점수/레벨/세부 특성(한글 라벨) 파싱
        def build_big5_text() -> str:
            trait_labels = {
                "openness": "경험에 대한 개방성",
                "conscientiousness": "성실성",
                "extraversion": "외향성",
                "agreeableness": "우호성",
                "neuroticism": "신셩증",
            }

            facet_label_maps = {
                "openness_facets": ["상상력", "예술성", "감정성", "모험성", "지성", "자유주의"],
                "conscientiousness_facets": ["자기효능감", "체계성", "의무감", "성취추구", "자기통제", "신중함"],
                "extraversion_facets": ["친화성", "사교성", "주장성", "활동성", "자극추구", "쾌활함"],
                "agreeableness_facets": ["신뢰", "도덕성", "이타성", "협력", "겸손", "공감"],
                "neuroticism_facets": ["불안", "분노", "우울", "자의식", "무절제", "취약성"],
            }

            lines = []

            # 점수 + 레벨
            lines.append(f"{trait_labels['openness']} 점수: {db_big5.openness_score}")
            lines.append(f"{trait_labels['openness']} 레벨: {db_big5.openness_level}")
            lines.append(f"{trait_labels['conscientiousness']} 점수: {db_big5.conscientiousness_score}")
            lines.append(f"{trait_labels['conscientiousness']} 레벨: {db_big5.conscientiousness_level}")
            lines.append(f"{trait_labels['extraversion']} 점수: {db_big5.extraversion_score}")
            lines.append(f"{trait_labels['extraversion']} 레벨: {db_big5.extraversion_level}")
            lines.append(f"{trait_labels['agreeableness']} 점수: {db_big5.agreeableness_score}")
            lines.append(f"{trait_labels['agreeableness']} 레벨: {db_big5.agreeableness_level}")
            lines.append(f"{trait_labels['neuroticism']} 점수: {db_big5.neuroticism_score}")
            lines.append(f"{trait_labels['neuroticism']} 레벨: {db_big5.neuroticism_level}")

            # 세부 특성
            def format_facets(facet_key: str, trait_prefix_ko: str, facets_dict: dict) -> str:
                if not facets_dict:
                    return ""
                labels = facet_label_maps[facet_key]
                parts = []
                # facets는 키가 "1".."6"
                for idx in range(1, 7):
                    key = str(idx)
                    label = labels[idx - 1]
                    value = facets_dict.get(key)
                    if value is not None:
                        parts.append(f"{trait_prefix_ko}_{label}:{value}")
                return ", ".join(parts)

            openness_facets_line = format_facets(
                "openness_facets", "개방성", getattr(db_big5, "openness_facets", None) or {}
            )
            conscientiousness_facets_line = format_facets(
                "conscientiousness_facets", "성실성", getattr(db_big5, "conscientiousness_facets", None) or {}
            )
            extraversion_facets_line = format_facets(
                "extraversion_facets", "외향성", getattr(db_big5, "extraversion_facets", None) or {}
            )
            agreeableness_facets_line = format_facets(
                "agreeableness_facets", "우호성", getattr(db_big5, "agreeableness_facets", None) or {}
            )
            neuroticism_facets_line = format_facets(
                "neuroticism_facets", "신경성", getattr(db_big5, "neuroticism_facets", None) or {}
            )

            if any([openness_facets_line, conscientiousness_facets_line, extraversion_facets_line, agreeableness_facets_line, neuroticism_facets_line]):
                lines.append("")
                if openness_facets_line:
                    lines.append(openness_facets_line)
                if conscientiousness_facets_line:
                    lines.append(conscientiousness_facets_line)
                if extraversion_facets_line:
                    lines.append(extraversion_facets_line)
                if agreeableness_facets_line:
                    lines.append(agreeableness_facets_line)
                if neuroticism_facets_line:
                    lines.append(neuroticism_facets_line)

            return "\n".join(lines)

        big5_text_summary = build_big5_text()

        # job_seekers.big5_text 업데이트 (job_seeker_id는 job_seekers.id 참조)
        job_seeker = self.db.query(JobSeeker).filter(JobSeeker.id == db_big5.job_seeker_id).first()
        if job_seeker and big5_text_summary is not None:
            job_seeker.big5_text = str(big5_text_summary)
            self.db.add(job_seeker)

        self.db.commit()
        self.db.refresh(db_big5)
        return db_big5
