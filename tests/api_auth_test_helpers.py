from uuid import UUID

from api.schemas.auth import CurrentUser

ACTIVE_TEST_USER = CurrentUser(
    user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    username="route.test",
    is_active=True,
    roles=["ReadOnly"],
)
