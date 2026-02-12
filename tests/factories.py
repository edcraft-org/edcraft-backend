"""Factory functions for creating test data."""

from typing import Any
from uuid import uuid4

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
from edcraft_backend.models.question_data import MCQData, MRQData, ShortAnswerData
from edcraft_backend.models.question_template import QuestionTemplate
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
        **overrides
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


async def create_test_question_template(
    db: AsyncSession, owner: User, **overrides: Any
) -> QuestionTemplate:
    """
    Create a test question template with sensible defaults.

    Args:
        db: Database session
        owner: User who owns the template
        **overrides: Field overrides (question_text, question_type, template_config, etc.)

    Returns:
        Created QuestionTemplate instance
    """
    unique_id = str(uuid4())[:8]
    defaults = {
        "owner_id": owner.id,
        "question_type": "mcq",
        "question_text": f"Template question {unique_id}?",
        "description": f"Test question template {unique_id}",
        "template_config": {
            "code": "def example(n):\n    return n * 2",
            "question_spec": {
                "target": [
                    {
                        "type": "function",
                        "id": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
                "output_type": "first",
                "question_type": "mcq",
            },
            "generation_options": {"num_distractors": 4},
            "entry_function": "example",
        },
    }
    defaults.update(overrides)

    template = QuestionTemplate(**defaults)
    db.add(template)
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


# Relationship Factories


async def link_question_to_assessment(
    db: AsyncSession, assessment: Assessment, question: Question, order: int = 0
) -> AssessmentQuestion:
    """
    Create AssessmentQuestion association linking a question to an assessment.

    Args:
        db: Database session
        assessment: Assessment to link to
        question: Question to link
        order: Display order of the question in the assessment

    Returns:
        Created AssessmentQuestion instance
    """
    assoc = AssessmentQuestion(
        assessment_id=assessment.id,
        question_id=question.id,
        order=order,
    )
    db.add(assoc)
    await db.flush()
    return assoc


async def link_question_template_to_assessment_template(
    db: AsyncSession,
    assessment_template: AssessmentTemplate,
    question_template: QuestionTemplate,
    order: int = 0,
) -> AssessmentTemplateQuestionTemplate:
    """
    Create association linking a question template to an assessment template.

    Args:
        db: Database session
        assessment_template: Assessment template to link to
        question_template: Question template to link
        order: Display order of the question template in the assessment template

    Returns:
        Created AssessmentTemplateQuestionTemplate instance
    """
    assoc = AssessmentTemplateQuestionTemplate(
        assessment_template_id=assessment_template.id,
        question_template_id=question_template.id,
        order=order,
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
        await link_question_to_assessment(db, assessment, question, order=i)

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
            db, assessment_template, question_template, order=i
        )

    return assessment_template, question_templates
