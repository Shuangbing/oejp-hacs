"""API client for Octo Energy JP GraphQL."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from aiohttp import ClientSession

from .models import HHReading

AUTH_BODY = """
mutation obtainKrakenToken($input: ObtainJSONWebTokenInput!) {
  obtainKrakenToken(input: $input) {
    token
  }
}
"""

GET_ACCOUNT_BODY = """
query accountViewer {
  viewer {
    accounts {
      number
    }
  }
}
"""

GET_HH_BODY = """
query halfHourlyReadings($accountNumber: String!, $fromDatetime: DateTime, $toDatetime: DateTime) {
  account(accountNumber: $accountNumber) {
    properties {
      electricitySupplyPoints {
        halfHourlyReadings(fromDatetime: $fromDatetime, toDatetime: $toDatetime) {
          startAt
          endAt
          version
          value
        }
      }
    }
  }
}
"""


class OctoEnergyJpApiError(Exception):
    """Base API error."""


class OctoEnergyJpAuthError(OctoEnergyJpApiError):
    """Authentication error."""


class OctoEnergyJpClient:
    """Small async client around OEJP GraphQL API."""

    def __init__(self, session: ClientSession, api_url: str) -> None:
        self._session = session
        self._api_url = api_url

    async def get_token(self, email: str, password: str) -> str:
        """Exchange email/password for JWT token."""
        data = await self._post_graphql(
            query=AUTH_BODY,
            variables={"input": {"email": email, "password": password}},
        )
        try:
            return data["obtainKrakenToken"]["token"]
        except KeyError as err:
            raise OctoEnergyJpAuthError("Authentication response was invalid") from err

    async def get_account_number(self, token: str) -> str:
        """Return the first account number from viewer."""
        data = await self._post_graphql(query=GET_ACCOUNT_BODY, token=token)
        try:
            return data["viewer"]["accounts"][0]["number"]
        except (KeyError, IndexError) as err:
            raise OctoEnergyJpApiError("Unable to resolve account number from response") from err

    async def get_hh_readings(
        self,
        account_number: str,
        token: str,
        start_at: datetime,
        end_at: datetime | None = None,
    ) -> list[HHReading]:
        """Return half-hourly readings for the given range."""
        variables: dict[str, Any] = {
            "accountNumber": account_number,
            "fromDatetime": start_at.isoformat(),
        }
        if end_at is not None:
            variables["toDatetime"] = end_at.isoformat()

        data = await self._post_graphql(
            query=GET_HH_BODY,
            variables=variables,
            token=token,
        )
        try:
            raw_readings = data["account"]["properties"][0]["electricitySupplyPoints"][0][
                "halfHourlyReadings"
            ]
        except (KeyError, IndexError) as err:
            raise OctoEnergyJpApiError("Unable to parse half-hourly readings response") from err

        readings: list[HHReading] = []
        for row in raw_readings:
            readings.append(
                HHReading(
                    start_at=datetime.fromisoformat(row["startAt"]),
                    end_at=datetime.fromisoformat(row["endAt"]),
                    version=row["version"],
                    value=Decimal(row["value"]),
                )
            )

        readings.sort(key=lambda x: x.end_at)
        return readings

    async def _post_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if token:
            headers["authorization"] = f"JWT {token}"

        async with self._session.post(
            self._api_url,
            json={"query": query, "variables": variables or {}},
            headers=headers,
        ) as response:
            payload = await response.json(content_type=None)

        errors = payload.get("errors")
        if errors:
            message = str(errors)
            if "invalid" in message.lower() or "credential" in message.lower():
                raise OctoEnergyJpAuthError(message)
            raise OctoEnergyJpApiError(message)

        data = payload.get("data")
        if data is None:
            raise OctoEnergyJpApiError("GraphQL response did not include data field")

        return data
