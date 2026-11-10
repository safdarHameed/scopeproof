from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, ProjectDep
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectStatsRead,
    ProjectSummary,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


async def _summary(db: DbSession, project) -> ProjectSummary:
    stats = (await project_service.stats_for(db, [project.id]))[project.id]
    return ProjectSummary(
        **ProjectRead.model_validate(project).model_dump(),
        stats=ProjectStatsRead(**stats.__dict__),
    )


@router.get("", response_model=list[ProjectSummary])
async def list_projects(db: DbSession, user: CurrentUser) -> list[ProjectSummary]:
    projects = await project_service.list_for_owner(db, user.id)
    stats = await project_service.stats_for(db, [p.id for p in projects])
    return [
        ProjectSummary(
            **ProjectRead.model_validate(p).model_dump(),
            stats=ProjectStatsRead(**stats[p.id].__dict__),
        )
        for p in projects
    ]


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: DbSession, user: CurrentUser) -> ProjectSummary:
    project = await project_service.create(db, user.id, data)
    return await _summary(db, project)


@router.get("/{project_id}", response_model=ProjectSummary)
async def get_project(project: ProjectDep, db: DbSession) -> ProjectSummary:
    return await _summary(db, project)


@router.patch("/{project_id}", response_model=ProjectSummary)
async def update_project(data: ProjectUpdate, project: ProjectDep, db: DbSession) -> ProjectSummary:
    project = await project_service.update(db, project, data)
    return await _summary(db, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project: ProjectDep, db: DbSession) -> None:
    await project_service.delete_project(db, project)
