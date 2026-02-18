from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from ..db.models import Tag
from ..db.session import get_db
from ..deps import get_current_user
from ..schemas import TagCreateRequest, TagOut

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[TagOut],
    summary="List tags",
    description="List all tags for the current user.",
    operation_id="list_tags",
)
async def list_tags(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[TagOut]:
    """List tags."""
    res = await db.execute(select(Tag).where(Tag.user_id == user.id).order_by(Tag.created_at.desc()))
    tags = res.scalars().all()
    return [TagOut(id=t.id, name=t.name, created_at=t.created_at) for t in tags]


@router.post(
    "",
    response_model=TagOut,
    summary="Create tag",
    description="Create a tag for the current user (unique per user).",
    operation_id="create_tag",
)
async def create_tag(
    payload: TagCreateRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> TagOut:
    """Create tag."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Tag name required")

    existing = (
        await db.execute(select(Tag).where(Tag.user_id == user.id, Tag.name == name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Tag already exists")

    tag = Tag(user_id=user.id, name=name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagOut(id=tag.id, name=tag.name, created_at=tag.created_at)


@router.delete(
    "/{tag_id}",
    summary="Delete tag",
    description="Delete a tag by id (current user only).",
    operation_id="delete_tag",
)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Delete tag."""
    res = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    tag = res.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Tag not found")

    await db.execute(delete(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    await db.commit()
    return {"ok": True}
