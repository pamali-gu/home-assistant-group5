"""Storage for auth models."""

from __future__ import annotations

from datetime import timedelta
import hmac
import itertools
from logging import getLogger
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import models
from .const import (
    ACCESS_TOKEN_EXPIRATION,
    GROUP_ID_ADMIN,
    GROUP_ID_READ_ONLY,
    GROUP_ID_USER,
    REFRESH_TOKEN_EXPIRATION,
)
from .permissions import system_policies
from .permissions.models import PermissionLookup

STORAGE_VERSION = 1
STORAGE_KEY = "auth"
GROUP_NAME_ADMIN = "Administrators"
GROUP_NAME_USER = "Users"
GROUP_NAME_READ_ONLY = "Read Only"

# We always save the auth store after we load it since
# we may migrate data and do not want to have to do it again
# but we don't want to do it during startup so we schedule
# the first save 5 minutes out knowing something else may
# want to save the auth store before then, and since Storage
# will honor the lower of the two delays, it will save it
# faster if something else saves it.
INITIAL_LOAD_SAVE_DELAY = 300

DEFAULT_SAVE_DELAY = 1


class AuthStore:
    """Stores authentication info.

    Any mutation to an object should happen inside the auth store.

    The auth store is lazy. It won't load the data from disk until a method is
    called that needs it.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the auth store."""
        self.hass = hass
        self._loaded = False
        self._users: dict[str, models.User] = None  # type: ignore[assignment]
        self._groups: dict[str, models.Group] = None  # type: ignore[assignment]
        self._perm_lookup: PermissionLookup | None
        self._store = Store[dict[str, list[dict[str, Any]]]](
            hass, STORAGE_VERSION, STORAGE_KEY, private=True, atomic_writes=True
        )
        self._token_id_to_user_id: dict[str, str] = {}

    async def async_get_groups(self) -> list[models.Group]:
        """Retrieve all users."""
        return list(self._groups.values())

    async def async_get_group(self, group_id: str) -> models.Group | None:
        """Retrieve all users."""
        return self._groups.get(group_id)

    async def async_get_users(self) -> list[models.User]:
        """Retrieve all users."""
        return list(self._users.values())

    async def async_get_user(self, user_id: str) -> models.User | None:
        """Retrieve a user by id."""
        return self._users.get(user_id)

    async def async_create_user(
        self,
        name: str | None,
        is_owner: bool | None = None,
        is_active: bool | None = None,
        system_generated: bool | None = None,
        credentials: models.Credentials | None = None,
        group_ids: list[str] | None = None,
        local_only: bool | None = None,
    ) -> models.User:
        """Create a new user."""
        groups = []
        for group_id in group_ids or []:
            if (group := self._groups.get(group_id)) is None:
                raise ValueError(f"Invalid group specified {group_id}")
            groups.append(group)

        kwargs: dict[str, Any] = {
            "name": name,
            # Until we get group management, we just put everyone in the
            # same group.
            "groups": groups,
            "perm_lookup": self._perm_lookup,
        }

        kwargs.update(
            {
                attr_name: value
                for attr_name, value in (
                    ("is_owner", is_owner),
                    ("is_active", is_active),
                    ("local_only", local_only),
                    ("system_generated", system_generated),
                )
                if value is not None
            }
        )

        new_user = models.User(**kwargs)

        self._users[new_user.id] = new_user

        if credentials is None:
            self._async_schedule_save()
            return new_user

        # Saving is done inside the link.
        await self.async_link_user(new_user, credentials)
        return new_user

    async def async_link_user(
        self, user: models.User, credentials: models.Credentials
    ) -> None:
        """Add credentials to an existing user."""
        user.credentials.append(credentials)
        self._async_schedule_save()
        credentials.is_new = False

    async def async_remove_user(self, user: models.User) -> None:
        """Remove a user."""
        user = self._users.pop(user.id)
        for refresh_token_id in user.refresh_tokens:
            del self._token_id_to_user_id[refresh_token_id]
        user.refresh_tokens.clear()
        self._async_schedule_save()

    async def async_update_user(
        self,
        user: models.User,
        name: str | None = None,
        is_active: bool | None = None,
        group_ids: list[str] | None = None,
        local_only: bool | None = None,
    ) -> None:
        """Update a user."""
        if group_ids is not None:
            groups = []
            for grid in group_ids:
                if (group := self._groups.get(grid)) is None:
                    raise ValueError("Invalid group specified.")
                groups.append(group)

            user.groups = groups

        for attr_name, value in (
            ("name", name),
            ("is_active", is_active),
            ("local_only", local_only),
        ):
            if value is not None:
                setattr(user, attr_name, value)

        self._async_schedule_save()

    async def async_activate_user(self, user: models.User) -> None:
        """Activate a user."""
        user.is_active = True
        self._async_schedule_save()

    async def async_deactivate_user(self, user: models.User) -> None:
        """Activate a user."""
        user.is_active = False
        self._async_schedule_save()

    async def async_remove_credentials(self, credentials: models.Credentials) -> None:
        """Remove credentials."""
        for user in self._users.values():
            found = None

            for index, cred in enumerate(user.credentials):
                if cred is credentials:
                    found = index
                    break

            if found is not None:
                user.credentials.pop(found)
                break

        self._async_schedule_save()

    async def async_create_refresh_token(
        self,
        user: models.User,
        client_id: str | None = None,
        client_name: str | None = None,
        client_icon: str | None = None,
        token_type: str = models.TOKEN_TYPE_NORMAL,
        access_token_expiration: timedelta = ACCESS_TOKEN_EXPIRATION,
        expire_at: float | None = None,
        credential: models.Credentials | None = None,
    ) -> models.RefreshToken:
        """Create a new token for a user."""
        kwargs: dict[str, Any] = {
            "user": user,
            "client_id": client_id,
            "token_type": token_type,
            "access_token_expiration": access_token_expiration,
            "expire_at": expire_at,
            "credential": credential,
        }
        if client_name:
            kwargs["client_name"] = client_name
        if client_icon:
            kwargs["client_icon"] = client_icon

        refresh_token = models.RefreshToken(**kwargs)
        token_id = refresh_token.id
        user.refresh_tokens[token_id] = refresh_token
        self._token_id_to_user_id[token_id] = user.id

        self._async_schedule_save()
        return refresh_token

    @callback
    def async_remove_refresh_token(self, refresh_token: models.RefreshToken) -> None:
        """Remove a refresh token."""
        refresh_token_id = refresh_token.id
        if user_id := self._token_id_to_user_id.get(refresh_token_id):
            del self._users[user_id].refresh_tokens[refresh_token_id]
            del self._token_id_to_user_id[refresh_token_id]
            self._async_schedule_save()

    @callback
    def async_get_refresh_token(self, token_id: str) -> models.RefreshToken | None:
        """Get refresh token by id."""
        if user_id := self._token_id_to_user_id.get(token_id):
            return self._users[user_id].refresh_tokens.get(token_id)
        return None

    @callback
    def async_get_refresh_token_by_token(
        self, token: str
    ) -> models.RefreshToken | None:
        """Get refresh token by token."""
        found = None

        for user in self._users.values():
            for refresh_token in user.refresh_tokens.values():
                if hmac.compare_digest(refresh_token.token, token):
                    found = refresh_token

        return found

    @callback
    def async_get_refresh_tokens(self) -> list[models.RefreshToken]:
        """Get all refresh tokens."""
        return list(
            itertools.chain.from_iterable(
                user.refresh_tokens.values() for user in self._users.values()
            )
        )

    @callback
    def async_log_refresh_token_usage(
        self, refresh_token: models.RefreshToken, remote_ip: str | None = None
    ) -> None:
        """Update refresh token last used information."""
        refresh_token.last_used_at = dt_util.utcnow()
        refresh_token.last_used_ip = remote_ip
        if refresh_token.expire_at:
            refresh_token.expire_at = (
                refresh_token.last_used_at.timestamp() + REFRESH_TOKEN_EXPIRATION
            )
        self._async_schedule_save()

    @callback
    def async_set_expiry(
        self, refresh_token: models.RefreshToken, *, enable_expiry: bool
    ) -> None:
        """Enable or disable expiry of a refresh token."""
        if enable_expiry:
            if refresh_token.expire_at is None:
                refresh_token.expire_at = (
                    refresh_token.last_used_at or dt_util.utcnow()
                ).timestamp() + REFRESH_TOKEN_EXPIRATION
                self._async_schedule_save()
        else:
            refresh_token.expire_at = None
            self._async_schedule_save()

    @callback
    def async_update_user_credentials_data(
        self, credentials: models.Credentials, data: dict[str, Any]
    ) -> None:
        """Update credentials data."""
        credentials.data = data
        self._async_schedule_save()

    async def async_load(self) -> None:  # noqa: C901
        """Load the users."""
        if self._loaded:
            raise RuntimeError("Auth storage is already loaded")
        self._loaded = True

        dev_reg = dr.async_get(self.hass)
        ent_reg = er.async_get(self.hass)
        data = await self._store.async_load()

        perm_lookup = PermissionLookup(ent_reg, dev_reg)
        self._perm_lookup = perm_lookup  # Ensure this is initialized properly

        if data is None or not isinstance(data, dict):
            self._set_defaults()
            return

        users: dict[str, models.User] = {}
        groups: dict[str, models.Group] = {}
        credentials: dict[str, models.Credentials] = {}

        has_groups = self._initialize_groups(data, groups)
        migrate_users_to_admin_group = (
            not groups and has_groups.get("group_without_policy") is None
        )

        if not has_groups.get("has_admin_group"):
            groups[GROUP_ID_ADMIN] = _system_admin_group()

        if not has_groups.get("has_read_only_group"):
            groups[GROUP_ID_READ_ONLY] = _system_read_only_group()

        if not has_groups.get("has_user_group"):
            groups[GROUP_ID_USER] = _system_user_group()

        self._load_users(data["users"], groups, users, migrate_users_to_admin_group)
        self._load_credentials(data["credentials"], users, credentials)
        self._load_refresh_tokens(data["refresh_tokens"], users, credentials)

        self._groups = groups
        self._users = users
        self._build_token_id_to_user_id()
        self._async_schedule_save(INITIAL_LOAD_SAVE_DELAY)

    def _initialize_groups(
        self, data: dict[str, Any], groups: dict[str, models.Group]
    ) -> dict[str, Any]:
        """Initialize groups from the loaded data."""
        has_admin_group = has_user_group = has_read_only_group = False
        group_without_policy = None

        for group_dict in data.get("groups", []):
            policy, name, system_generated = self._get_group_policy(group_dict)
            if policy is None and not system_generated:
                group_without_policy = group_dict["id"]
                continue

            groups[group_dict["id"]] = models.Group(
                id=group_dict["id"],
                name=name,
                policy=policy,
                system_generated=system_generated,
            )

            if group_dict["id"] == GROUP_ID_ADMIN:
                has_admin_group = True
            elif group_dict["id"] == GROUP_ID_USER:
                has_user_group = True
            elif group_dict["id"] == GROUP_ID_READ_ONLY:
                has_read_only_group = True

        return {
            "has_admin_group": has_admin_group,
            "has_user_group": has_user_group,
            "has_read_only_group": has_read_only_group,
            "group_without_policy": group_without_policy,
        }

    def _get_group_policy(self, group_dict: dict[str, Any]) -> tuple[Any, str, bool]:
        """Retrieve the policy for a group."""
        if group_dict["id"] == GROUP_ID_ADMIN:
            return system_policies.ADMIN_POLICY, GROUP_NAME_ADMIN, True
        if group_dict["id"] == GROUP_ID_USER:
            return system_policies.USER_POLICY, GROUP_NAME_USER, True
        if group_dict["id"] == GROUP_ID_READ_ONLY:
            return system_policies.READ_ONLY_POLICY, GROUP_NAME_READ_ONLY, True
        return group_dict.get("policy"), group_dict["name"], False

    def _load_users(
        self,
        users_data: list[dict[str, Any]],
        groups: dict[str, models.Group],
        users: dict[str, models.User],
        migrate_to_admin: bool,
    ) -> None:
        """Load users from the data."""
        for user_dict in users_data:
            user_groups = self._get_user_groups(user_dict, groups, migrate_to_admin)

            if self._perm_lookup is None:
                raise RuntimeError("Permission lookup has not been initialized")

            users[user_dict["id"]] = models.User(
                name=user_dict["name"],
                groups=user_groups,
                id=user_dict["id"],
                is_owner=user_dict["is_owner"],
                is_active=user_dict["is_active"],
                system_generated=user_dict["system_generated"],
                perm_lookup=self._perm_lookup,  # This should be non-null
                local_only=user_dict.get("local_only", False),
            )

    def _get_user_groups(
        self,
        user_dict: dict[str, Any],
        groups: dict[str, models.Group],
        migrate_to_admin: bool,
    ) -> list[models.Group]:
        """Retrieve the groups for a user."""
        user_groups: list[models.Group] = []
        for group_id in user_dict.get("group_ids", []):
            if group_id == GROUP_ID_USER:  # Migration from state 1
                group_id = GROUP_ID_ADMIN
            user_groups.append(groups[group_id])

        if not user_dict["system_generated"] and migrate_to_admin:
            user_groups.append(groups[GROUP_ID_ADMIN])

        return user_groups

    def _load_credentials(
        self,
        credentials_data: list[dict[str, Any]],
        users: dict[str, models.User],
        credentials: dict[str, models.Credentials],
    ) -> None:
        """Load credentials from the data."""
        for cred_dict in credentials_data:
            credential = models.Credentials(
                id=cred_dict["id"],
                is_new=False,
                auth_provider_type=cred_dict["auth_provider_type"],
                auth_provider_id=cred_dict["auth_provider_id"],
                data=cred_dict["data"],
            )
            credentials[cred_dict["id"]] = credential
            users[cred_dict["user_id"]].credentials.append(credential)

    def _load_refresh_tokens(
        self,
        tokens_data: list[dict[str, Any]],
        users: dict[str, models.User],
        credentials: dict[str, models.Credentials],
    ) -> None:
        """Load refresh tokens from the data."""
        for rt_dict in tokens_data:
            if "jwt_key" not in rt_dict:
                continue

            created_at_str = rt_dict.get("created_at")
            if not isinstance(created_at_str, str):
                getLogger(__name__).error(
                    "Ignoring refresh token %(id)s with invalid created_at type for user_id %(user_id)s",
                    rt_dict,
                )
                continue

            created_at = dt_util.parse_datetime(created_at_str)
            if created_at is None:
                getLogger(__name__).error(
                    (
                        "Ignoring refresh token %(id)s with invalid created_at "
                        "%(created_at)s for user_id %(user_id)s"
                    ),
                    rt_dict,
                )
                continue

            token_type = rt_dict.get(
                "token_type",
                models.TOKEN_TYPE_SYSTEM
                if rt_dict["client_id"] is None
                else models.TOKEN_TYPE_NORMAL,
            )

            last_used_at_raw = rt_dict.get("last_used_at")
            last_used_at = (
                dt_util.parse_datetime(last_used_at_raw)
                if isinstance(last_used_at_raw, str)
                else None
            )

            token = models.RefreshToken(
                id=rt_dict["id"],
                user=users[rt_dict["user_id"]],
                client_id=rt_dict["client_id"],
                client_name=rt_dict.get("client_name"),
                client_icon=rt_dict.get("client_icon"),
                token_type=token_type,
                created_at=created_at,
                access_token_expiration=timedelta(
                    seconds=rt_dict["access_token_expiration"]
                ),
                token=rt_dict["token"],
                jwt_key=rt_dict["jwt_key"],
                last_used_at=last_used_at,
                last_used_ip=rt_dict.get("last_used_ip"),
                expire_at=rt_dict.get("expire_at"),
                version=rt_dict.get("version"),
            )

            if "credential_id" in rt_dict:
                token.credential = credentials.get(rt_dict["credential_id"])

            users[rt_dict["user_id"]].refresh_tokens[token.id] = token

    @callback
    def _build_token_id_to_user_id(self) -> None:
        """Build a map of token id to user id."""
        self._token_id_to_user_id = {
            token_id: user_id
            for user_id, user in self._users.items()
            for token_id in user.refresh_tokens
        }

    @callback
    def _async_schedule_save(self, delay: float = DEFAULT_SAVE_DELAY) -> None:
        """Save users."""
        self._store.async_delay_save(self._data_to_save, delay)

    @callback
    def _data_to_save(self) -> dict[str, list[dict[str, Any]]]:
        """Return the data to store."""
        users = [
            {
                "id": user.id,
                "group_ids": [group.id for group in user.groups],
                "is_owner": user.is_owner,
                "is_active": user.is_active,
                "name": user.name,
                "system_generated": user.system_generated,
                "local_only": user.local_only,
            }
            for user in self._users.values()
        ]

        groups = []
        for group in self._groups.values():
            g_dict: dict[str, Any] = {
                "id": group.id,
                # Name not read for sys groups. Kept here for backwards compat
                "name": group.name,
            }

            if not group.system_generated:
                g_dict["policy"] = group.policy

            groups.append(g_dict)

        credentials = [
            {
                "id": credential.id,
                "user_id": user.id,
                "auth_provider_type": credential.auth_provider_type,
                "auth_provider_id": credential.auth_provider_id,
                "data": credential.data,
            }
            for user in self._users.values()
            for credential in user.credentials
        ]

        refresh_tokens = [
            {
                "id": refresh_token.id,
                "user_id": user.id,
                "client_id": refresh_token.client_id,
                "client_name": refresh_token.client_name,
                "client_icon": refresh_token.client_icon,
                "token_type": refresh_token.token_type,
                "created_at": refresh_token.created_at.isoformat(),
                "access_token_expiration": (
                    refresh_token.access_token_expiration.total_seconds()
                ),
                "token": refresh_token.token,
                "jwt_key": refresh_token.jwt_key,
                "last_used_at": refresh_token.last_used_at.isoformat()
                if refresh_token.last_used_at
                else None,
                "last_used_ip": refresh_token.last_used_ip,
                "expire_at": refresh_token.expire_at,
                "credential_id": refresh_token.credential.id
                if refresh_token.credential
                else None,
                "version": refresh_token.version,
            }
            for user in self._users.values()
            for refresh_token in user.refresh_tokens.values()
        ]

        return {
            "users": users,
            "groups": groups,
            "credentials": credentials,
            "refresh_tokens": refresh_tokens,
        }

    def _set_defaults(self) -> None:
        """Set default values for auth store."""
        self._users = {}

        groups: dict[str, models.Group] = {}
        admin_group = _system_admin_group()
        groups[admin_group.id] = admin_group
        user_group = _system_user_group()
        groups[user_group.id] = user_group
        read_only_group = _system_read_only_group()
        groups[read_only_group.id] = read_only_group
        self._groups = groups
        self._build_token_id_to_user_id()


def _system_admin_group() -> models.Group:
    """Create system admin group."""
    return models.Group(
        name=GROUP_NAME_ADMIN,
        id=GROUP_ID_ADMIN,
        policy=system_policies.ADMIN_POLICY,
        system_generated=True,
    )


def _system_user_group() -> models.Group:
    """Create system user group."""
    return models.Group(
        name=GROUP_NAME_USER,
        id=GROUP_ID_USER,
        policy=system_policies.USER_POLICY,
        system_generated=True,
    )


def _system_read_only_group() -> models.Group:
    """Create read only group."""
    return models.Group(
        name=GROUP_NAME_READ_ONLY,
        id=GROUP_ID_READ_ONLY,
        policy=system_policies.READ_ONLY_POLICY,
        system_generated=True,
    )
