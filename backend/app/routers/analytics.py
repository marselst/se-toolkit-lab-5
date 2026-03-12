"""Router for analytics endpoints.

Each endpoint performs SQL aggregation queries on the interaction data
populated by the ETL pipeline. All endpoints require a `lab` query
parameter to filter results by lab (e.g., "lab-01").
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.item import ItemRecord
from app.models.learner import Learner
from app.models.interaction import InteractionLog

router = APIRouter()


@router.get("/scores")
async def get_scores(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Score distribution histogram for a given lab."""
    lab_title = lab.replace("-", " ").title()
    lab_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "lab",
        func.lower(ItemRecord.title).contains(func.lower(lab_title))
    )
    lab_result = await session.exec(lab_stmt)
    lab_id_row = lab_result.one_or_none()
    lab_id = lab_id_row[0] if lab_id_row else None

    if lab_id is None:
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0},
        ]

    task_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_id
    )
    task_result = await session.exec(task_stmt)
    task_ids = [row[0] for row in task_result.all()]

    if not task_ids:
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0},
        ]

    score_bucket = case(
        (InteractionLog.score <= 25, "0-25"),
        (InteractionLog.score <= 50, "26-50"),
        (InteractionLog.score <= 75, "51-75"),
        else_="76-100",
    ).label("bucket")

    stmt = select(
        score_bucket,
        func.count().label("count")
    ).where(
        InteractionLog.item_id.in_(task_ids),
        InteractionLog.score.isnot(None)
    ).group_by(score_bucket)

    result = await session.exec(stmt)
    bucket_counts = {row.bucket: row.count for row in result.all()}

    return [
        {"bucket": "0-25", "count": bucket_counts.get("0-25", 0)},
        {"bucket": "26-50", "count": bucket_counts.get("26-50", 0)},
        {"bucket": "51-75", "count": bucket_counts.get("51-75", 0)},
        {"bucket": "76-100", "count": bucket_counts.get("76-100", 0)},
    ]


@router.get("/pass-rates")
async def get_pass_rates(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Per-task pass rates for a given lab."""
    lab_title = lab.replace("-", " ").title()
    lab_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "lab",
        func.lower(ItemRecord.title).contains(func.lower(lab_title))
    )
    lab_result = await session.exec(lab_stmt)
    lab_id_row = lab_result.one_or_none()
    lab_id = lab_id_row[0] if lab_id_row else None

    if lab_id is None:
        return []

    task_stmt = select(ItemRecord.id, ItemRecord.title).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_id
    ).order_by(ItemRecord.title)
    task_result = await session.exec(task_stmt)
    tasks = [(row[0], row[1]) for row in task_result.all()]

    result = []
    for task_id, task_title in tasks:
        stmt = select(
            func.avg(InteractionLog.score).label("avg_score"),
            func.count().label("attempts")
        ).where(
            InteractionLog.item_id == task_id,
            InteractionLog.score.isnot(None)
        )
        query_result = await session.exec(stmt)
        row = query_result.first()

        avg_score = round(row.avg_score, 1) if row.avg_score is not None else 0.0
        attempts = row.attempts if row.attempts is not None else 0

        result.append({
            "task": task_title,
            "avg_score": avg_score,
            "attempts": attempts,
        })

    return result


@router.get("/timeline")
async def get_timeline(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Submissions per day for a given lab."""
    lab_title = lab.replace("-", " ").title()
    lab_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "lab",
        func.lower(ItemRecord.title).contains(func.lower(lab_title))
    )
    lab_result = await session.exec(lab_stmt)
    lab_id_row = lab_result.one_or_none()
    lab_id = lab_id_row[0] if lab_id_row else None

    if lab_id is None:
        return []

    task_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_id
    )
    task_result = await session.exec(task_stmt)
    task_ids = [row[0] for row in task_result.all()]

    if not task_ids:
        return []

    stmt = select(
        func.date(InteractionLog.created_at).label("date"),
        func.count().label("submissions")
    ).where(
        InteractionLog.item_id.in_(task_ids)
    ).group_by(
        func.date(InteractionLog.created_at)
    ).order_by(
        func.date(InteractionLog.created_at)
    )

    result = await session.exec(stmt)
    return [
        {"date": str(row.date), "submissions": row.submissions}
        for row in result.all()
    ]


@router.get("/groups")
async def get_groups(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Per-group performance for a given lab."""
    lab_title = lab.replace("-", " ").title()
    lab_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "lab",
        func.lower(ItemRecord.title).contains(func.lower(lab_title))
    )
    lab_result = await session.exec(lab_stmt)
    lab_id_row = lab_result.one_or_none()
    lab_id = lab_id_row[0] if lab_id_row else None

    if lab_id is None:
        return []

    task_stmt = select(ItemRecord.id).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_id
    )
    task_result = await session.exec(task_stmt)
    task_ids = [row[0] for row in task_result.all()]

    if not task_ids:
        return []

    stmt = select(
        Learner.student_group.label("group"),
        func.avg(InteractionLog.score).label("avg_score"),
        func.count(func.distinct(Learner.id)).label("students")
    ).join(
        InteractionLog, InteractionLog.learner_id == Learner.id
    ).where(
        InteractionLog.item_id.in_(task_ids),
        InteractionLog.score.isnot(None)
    ).group_by(
        Learner.student_group
    ).order_by(
        Learner.student_group
    )

    result = await session.exec(stmt)
    return [
        {
            "group": row.group,
            "avg_score": round(row.avg_score, 1) if row.avg_score is not None else 0.0,
            "students": row.students,
        }
        for row in result.all()
    ]
