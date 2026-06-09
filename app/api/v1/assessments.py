from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, AuthenticatedUser
from app.repositories.repositories import QuestionnaireRepository, VendorRepository
from app.schemas.schemas import (
    QuestionnaireCreateRequest, QuestionnaireResponse,
    QuestionnaireStatusUpdateRequest
)

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.get("/vendor/{vendor_id}", response_model=list[QuestionnaireResponse])
async def list_questionnaires(
    vendor_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    questionnaires = await QuestionnaireRepository.get_all_by_vendor(
        db, current_user.tenant_id, vendor_id
    )
    return [QuestionnaireResponse.model_validate(q) for q in questionnaires]


@router.post("", response_model=QuestionnaireResponse, status_code=status.HTTP_201_CREATED)
async def create_questionnaire(
    body: QuestionnaireCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, body.vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    questions_data = [q.model_dump() for q in body.questions]

    questionnaire = await QuestionnaireRepository.create(
        db,
        tenant_id=current_user.tenant_id,
        vendor_id=body.vendor_id,
        title=body.title,
        due_date=body.due_date,
        questions_data=questions_data,
        analyst_id=current_user.user_id,
    )

    result = await QuestionnaireRepository.get_by_id(
        db, questionnaire.id, current_user.tenant_id
    )
    return QuestionnaireResponse.model_validate(result)


@router.get("/{questionnaire_id}", response_model=QuestionnaireResponse)
async def get_questionnaire(
    questionnaire_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    questionnaire = await QuestionnaireRepository.get_by_id(
        db, questionnaire_id, current_user.tenant_id
    )
    if not questionnaire:
        raise HTTPException(status_code=404, detail="Questionnaire not found.")
    return QuestionnaireResponse.model_validate(questionnaire)


@router.patch("/{questionnaire_id}/status", response_model=QuestionnaireResponse)
async def update_questionnaire_status(
    questionnaire_id: UUID,
    body: QuestionnaireStatusUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    questionnaire = await QuestionnaireRepository.get_by_id(
        db, questionnaire_id, current_user.tenant_id
    )
    if not questionnaire:
        raise HTTPException(status_code=404, detail="Questionnaire not found.")

    updated = await QuestionnaireRepository.update_status(
        db, questionnaire_id, current_user.tenant_id, body.status
    )
    return QuestionnaireResponse.model_validate(updated)