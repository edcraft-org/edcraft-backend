"""Factory functions for creating test data."""

from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.assessment_template_question_template import (
    AssessmentTemplateQuestionTemplate,
)
from edcraft_backend.models.folder import Folder
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.models.question_bank_question import QuestionBankQuestion
from edcraft_backend.models.question_data import MCQData, MRQData, ShortAnswerData
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.models.question_template_bank_question_template import (
    QuestionTemplateBankQuestionTemplate,
)
from edcraft_backend.models.user import User

# Auth Helpers


async def create_and_login_user(
    test_client: AsyncClient, db_session: AsyncSession
) -> User:
    """Create a user via signup API and login to set auth cookies on the client.

    Args:
        test_client: HTTP test client \\
        db_session: Database session to retrieve the created user

    Returns:
        Created User instance
    """
    unique_id = str(uuid4())[:8]
    email = f"test_{unique_id}@example.com"
    password = "TestPassword123!"  # noqa S106

    await test_client.post("/auth/signup", json={"email": email, "password": password})
    await test_client.post("/auth/login", json={"email": email, "password": password})

    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


# Core Factories


async def create_test_user(db: AsyncSession, **overrides: Any) -> User:
    """
    Create a test user with sensible defaults.

    Args:
        db: Database session
        **overrides: Field overrides (email, name, etc.)

    Returns:
        Created User instance
    """
    unique_id = str(uuid4())[:8]
    defaults = {
        "email": f"test_{unique_id}@example.com",
        "name": f"testuser_{unique_id}",
    }
    defaults.update(overrides)

    user = User(**defaults)
    db.add(user)
    await db.flush()

    root_folder = Folder(owner_id=user.id, parent_id=None, name="My Projects")
    db.add(root_folder)
    await db.flush()

    return user


async def get_user_root_folder(db: AsyncSession, owner: User) -> Folder:
    """
    Get the root folder for a user.

    Args:
        db: Database session
        owner: User who owns the folder

    Returns:
        Root Folder instance

    Raises:
        ValueError: If user has no root folder
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Folder).where(
            Folder.owner_id == owner.id,
            Folder.parent_id.is_(None),
            Folder.deleted_at.is_(None),
        )
    )
    root_folder = result.scalar_one_or_none()
    if not root_folder:
        raise ValueError(f"User {owner.id} has no root folder")
    return root_folder


async def create_test_folder(
    db: AsyncSession, owner: User, parent: Folder | None = None, **overrides: Any
) -> Folder:
    """
    Create a test folder with sensible defaults.

    If no parent is provided, the folder will be created under the user's root folder.

    Args:
        db: Database session
        owner: User who owns the folder
        parent: Parent folder (optional, defaults to user's root folder)
        **overrides: Field overrides (name, description, etc.)

    Returns:
        Created Folder instance
    """
    unique_id = str(uuid4())[:8]

    if parent is None:
        parent = await get_user_root_folder(db, owner)

    defaults = {
        "owner_id": owner.id,
        "parent_id": parent.id,
        "name": f"Test Folder {unique_id}",
        "description": "Test folder description",
    }
    defaults.update(overrides)

    folder = Folder(**defaults)
    db.add(folder)
    await db.flush()
    return folder


async def create_test_question(
    db: AsyncSession,
    owner: User,
    template: QuestionTemplate | None = None,
    **overrides: Any,
) -> Question:
    """
    Create a test question with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the question
        template: Question template (optional)
        **overrides: Field overrides (question_text, question_type, etc.)

    Returns:
        Created Question instance
    """
    unique_id = str(uuid4())[:8]

    # Base question fields
    question_type = overrides.pop("question_type", "mcq")
    question_text = overrides.pop("question_text", f"Test question {unique_id}?")

    # Extract type-specific data from overrides
    options = overrides.pop("options", ["Option A", "Option B", "Option C", "Option D"])
    correct_index = overrides.pop("correct_index", 0)
    correct_indices = overrides.pop("correct_indices", [0])
    correct_answer = overrides.pop("correct_answer", "Test answer")

    # Create base question
    question = Question(
        owner_id=owner.id,
        template_id=template.id if template else None,
        question_type=question_type,
        question_text=question_text,
        **overrides,
    )

    # Create type-specific data
    if question_type == "mcq":
        question.mcq_data = MCQData(
            options=options,
            correct_index=correct_index,
        )
    elif question_type == "mrq":
        question.mrq_data = MRQData(
            options=options,
            correct_indices=correct_indices,
        )
    elif question_type == "short_answer":
        question.short_answer_data = ShortAnswerData(
            correct_answer=correct_answer,
        )

    db.add(question)
    await db.flush()
    return question


async def create_test_assessment(
    db: AsyncSession, owner: User, folder: Folder | None = None, **overrides: Any
) -> Assessment:
    """
    Create a test assessment with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the assessment
        folder: Folder containing the assessment (if None, uses owner's root folder)
        **overrides: Field overrides (title, description, etc.)

    Returns:
        Created Assessment instance
    """
    if folder is None:
        folder = await get_user_root_folder(db, owner)

    unique_id = str(uuid4())[:8]
    defaults = {
        "owner_id": owner.id,
        "folder_id": folder.id,
        "title": f"Test Assessment {unique_id}",
        "description": "Test assessment description",
    }
    defaults.update(overrides)

    assessment = Assessment(**defaults)
    db.add(assessment)
    await db.flush()
    return assessment


async def create_test_question_bank(
    db: AsyncSession, owner: User, folder: Folder | None = None, **overrides: Any
) -> QuestionBank:
    """
    Create a test question bank with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the question bank
        folder: Folder containing the bank (if None, uses owner's root folder)
        **overrides: Field overrides (title, description, etc.)

    Returns:
        Created QuestionBank instance
    """

    if folder is None:
        folder = await get_user_root_folder(db, owner)

    unique_id = str(uuid4())[:8]
    defaults = {
        "owner_id": owner.id,
        "folder_id": folder.id,
        "title": f"Test Question Bank {unique_id}",
        "description": "Test question bank description",
    }
    defaults.update(overrides)

    question_bank = QuestionBank(**defaults)
    db.add(question_bank)
    await db.flush()
    return question_bank


async def create_test_question_template(
    db: AsyncSession, owner: User, **overrides: Any
) -> QuestionTemplate:
    """
    Create a test question template with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the template
        **overrides: Field overrides (question_text, question_type, code, etc.)

    Returns:
        Created QuestionTemplate instance
    """
    from edcraft_backend.models.enums import OutputType, QuestionType
    from edcraft_backend.models.target_element import TargetElement

    unique_id = str(uuid4())[:8]
    defaults = {
        "owner_id": owner.id,
        "question_type": "mcq",
        "question_text": f"Template question {unique_id}?",
        "description": f"Test question template {unique_id}",
        "code": "def example(n):\n    return n * 2",
        "entry_function": "example",
        "num_distractors": 4,
        "output_type": "first",
    }
    defaults.update(overrides)

    target_elements_data = defaults.pop("target_elements", None)

    # Convert string enum values to actual enum instances
    if isinstance(defaults.get("question_type"), str):
        defaults["question_type"] = QuestionType(defaults["question_type"])
    if isinstance(defaults.get("output_type"), str):
        defaults["output_type"] = OutputType(defaults["output_type"])

    template = QuestionTemplate(**defaults)
    db.add(template)
    await db.flush()

    # Create target elements if provided, otherwise use defaults
    from edcraft_backend.models.enums import TargetElementType, TargetModifier

    if target_elements_data is None:
        target_element = TargetElement(
            template_id=template.id,
            order=0,
            element_type=TargetElementType.FUNCTION,
            id_list=[0],
            name="example",
            line_number=1,
            modifier=TargetModifier.RETURN_VALUE,
        )
        db.add(target_element)
    else:
        elem_data: dict[str, Any]
        for i, elem_data in enumerate(target_elements_data):  # type: ignore
            # Convert string enum values to actual enum instances
            if isinstance(elem_data.get("element_type"), str):
                elem_data["element_type"] = TargetElementType(elem_data["element_type"])
            if isinstance(elem_data.get("modifier"), str):
                elem_data["modifier"] = TargetModifier(elem_data["modifier"])

            target_element = TargetElement(
                template_id=template.id,
                order=i,
                **elem_data,
            )
            db.add(target_element)

    await db.flush()
    return template


async def create_test_assessment_template(
    db: AsyncSession, owner: User, folder: Folder | None = None, **overrides: Any
) -> AssessmentTemplate:
    """
    Create a test assessment template with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the template
        folder: Folder containing the template (if None, uses owner's root folder)
        **overrides: Field overrides (title, description, etc.)

    Returns:
        Created AssessmentTemplate instance
    """
    if folder is None:
        folder = await get_user_root_folder(db, owner)

    unique_id = str(uuid4())[:8]
    defaults = {
        "owner_id": owner.id,
        "folder_id": folder.id,
        "title": f"Test Assessment Template {unique_id}",
        "description": "Test assessment template description",
    }
    defaults.update(overrides)

    template = AssessmentTemplate(**defaults)
    db.add(template)
    await db.flush()
    return template


async def create_test_question_template_bank(
    db: AsyncSession, owner: User, folder: Folder | None = None, **overrides: Any
) -> QuestionTemplateBank:
    """
    Create a test question template bank with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the question template bank
        folder: Folder containing the bank (if None, uses owner's root folder)
        **overrides: Field overrides (title, description, etc.)

    Returns:
        Created QuestionTemplateBank instance
    """
    if folder is None:
        folder = await get_user_root_folder(db, owner)

    unique_id = str(uuid4())[:8]
    defaults = {
        "owner_id": owner.id,
        "folder_id": folder.id,
        "title": f"Test Question Template Bank {unique_id}",
        "description": "Test question template bank description",
    }
    defaults.update(overrides)

    question_template_bank = QuestionTemplateBank(**defaults)
    db.add(question_template_bank)
    await db.flush()
    return question_template_bank


# Relationship Factories


async def link_question_to_assessment(
    db: AsyncSession, assessment_id: UUID, question_id: UUID, order: int = 0
) -> AssessmentQuestion:
    """
    Create AssessmentQuestion association linking a question to an assessment.

    Args:
        db: Database session
        assessment_id: ID of the assessment to link to
        question_id: ID of the question to link
        order: Display order of the question in the assessment

    Returns:
        Created AssessmentQuestion instance
    """
    assoc = AssessmentQuestion(
        assessment_id=assessment_id,
        question_id=question_id,
        order=order,
    )
    db.add(assoc)
    await db.flush()
    return assoc


async def link_question_to_question_bank(
    db: AsyncSession, question_bank_id: UUID, question_id: UUID
) -> QuestionBankQuestion:
    """
    Create QuestionBankQuestion association linking a question to a question bank.

    Args:
        db: Database session
        question_bank_id: ID of the question bank to link to
        question_id: ID of the question to link

    Returns:
        Created QuestionBankQuestion instance
    """

    assoc = QuestionBankQuestion(
        question_bank_id=question_bank_id,
        question_id=question_id,
    )
    db.add(assoc)
    await db.flush()
    return assoc


async def link_question_template_to_assessment_template(
    db: AsyncSession,
    assessment_template_id: UUID,
    question_template_id: UUID,
    order: int = 0,
) -> AssessmentTemplateQuestionTemplate:
    """
    Create association linking a question template to an assessment template.

    Args:
        db: Database session
        assessment_template_id: ID of the assessment template to link to
        question_template_id: ID of the question template to link
        order: Display order of the question template in the assessment template

    Returns:
        Created AssessmentTemplateQuestionTemplate instance
    """
    assoc = AssessmentTemplateQuestionTemplate(
        assessment_template_id=assessment_template_id,
        question_template_id=question_template_id,
        order=order,
    )
    db.add(assoc)
    await db.flush()
    return assoc


async def link_question_template_to_question_template_bank(
    db: AsyncSession, question_template_bank_id: UUID, question_template_id: UUID
) -> QuestionTemplateBankQuestionTemplate:
    """
    Create association linking a question template to a question template bank.

    Args:
        db: Database session
        question_template_bank_id: ID of the question template bank to link to
        question_template_id: ID of the question template to link

    Returns:
        Created QuestionTemplateBankQuestionTemplate instance
    """
    assoc = QuestionTemplateBankQuestionTemplate(
        question_template_bank_id=question_template_bank_id,
        question_template_id=question_template_id,
    )
    db.add(assoc)
    await db.flush()
    return assoc


# Composite Factories


async def create_test_folder_tree(
    db: AsyncSession,
    owner: User,
    depth: int = 3,
    parent: Folder | None = None,
    _level: int = 0,
) -> list[Folder]:
    """
    Create a nested folder hierarchy for testing tree operations.

    Creates a tree structure with configurable depth.
    Example with depth=3:
    Root
    ├── Child 1
    │   └── Grandchild 1
    └── Child 2
        └── Grandchild 2

    Args:
        db: Database session
        owner: User who owns the folders
        depth: Maximum depth of the tree (default 3 levels)
        parent: Parent folder (internal use for recursion)
        _level: Current level (internal use for recursion)

    Returns:
        List of all created folders (breadth-first order)
    """
    if _level >= depth:
        return []

    folders = []

    # Determine number of folders at this level (1 root, 2 children per level)
    num_folders = 1 if _level == 0 else 2

    for i in range(num_folders):
        # Create descriptive name based on level
        if _level == 0:
            name = "Root Folder"
        elif _level == 1:
            name = f"Child {i + 1}"
        elif _level == 2:
            name = f"Grandchild {i + 1}"
        else:
            name = f"Level {_level} Folder {i + 1}"

        folder = await create_test_folder(db, owner, parent=parent, name=name)
        folders.append(folder)

        # Recursively create children
        children = await create_test_folder_tree(
            db, owner, depth=depth, parent=folder, _level=_level + 1
        )
        folders.extend(children)

    return folders


async def create_assessment_with_questions(
    db: AsyncSession, owner: User, num_questions: int = 3
) -> tuple[Assessment, list[Question]]:
    """
    Create an assessment with linked questions.

    Args:
        db: Database session
        owner: User who owns the assessment and questions
        num_questions: Number of questions to create and link

    Returns:
        Tuple of (Assessment, list of Questions)
    """
    assessment = await create_test_assessment(db, owner)
    questions = []

    for i in range(num_questions):
        question = await create_test_question(
            db, owner, question_text=f"Question {i + 1} in assessment?"
        )
        questions.append(question)
        await link_question_to_assessment(db, assessment.id, question.id, order=i)

    return assessment, questions


async def create_assessment_template_with_question_templates(
    db: AsyncSession, owner: User, num_templates: int = 3
) -> tuple[AssessmentTemplate, list[QuestionTemplate]]:
    """
    Create an assessment template with linked question templates.

    Args:
        db: Database session
        owner: User who owns the templates
        num_templates: Number of question templates to create and link

    Returns:
        Tuple of (AssessmentTemplate, list of QuestionTemplates)
    """
    assessment_template = await create_test_assessment_template(db, owner)
    question_templates = []

    for i in range(num_templates):
        question_template = await create_test_question_template(
            db, owner, question_text=f"Template question {i + 1}?"
        )
        question_templates.append(question_template)
        await link_question_template_to_assessment_template(
            db, assessment_template.id, question_template.id, order=i
        )

    return assessment_template, question_templates


async def create_question_template_bank_with_templates(
    db: AsyncSession, owner: User, num_templates: int = 3
) -> tuple[QuestionTemplateBank, list[QuestionTemplate]]:
    """
    Create a question template bank with linked question templates.

    Args:
        db: Database session
        owner: User who owns the templates
        num_templates: Number of question templates to create and link

    Returns:
        Tuple of (QuestionTemplateBank, list of QuestionTemplates)
    """
    question_template_bank = await create_test_question_template_bank(db, owner)
    question_templates = []

    for i in range(num_templates):
        question_template = await create_test_question_template(
            db, owner, question_text=f"Bank template question {i + 1}?"
        )
        question_templates.append(question_template)
        await link_question_template_to_question_template_bank(
            db, question_template_bank.id, question_template.id
        )

    return question_template_bank, question_templates
