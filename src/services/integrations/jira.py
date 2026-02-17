"""Jira integration for ticket creation and management."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from src.services.integrations.base import BaseIntegration

logger = logging.getLogger(__name__)


class JiraIntegration(BaseIntegration):
    """Jira integration for creating and managing incident tickets."""

    def __init__(
        self,
        url: str,
        username: str,
        api_token: str,
        project_key: str = "INC",
        issue_type: str = "Bug",
    ):
        self.url = url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.project_key = project_key
        self.issue_type = issue_type
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.url}/rest/api/3",
                auth=(self.username, self.api_token),
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def test_connection(self) -> bool:
        """Test connection to Jira."""
        try:
            response = await self.client.get("/myself")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False

    async def create_ticket(
        self,
        summary: str,
        description: str,
        priority: str = "Medium",
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Jira ticket for an incident.
        
        Args:
            summary: Ticket summary/title
            description: Detailed description (supports Jira markup)
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: List of labels to apply
            components: List of component names
            custom_fields: Additional custom fields
            incident_id: Optional incident ID to link
            
        Returns:
            Created ticket data including key and URL
        """
        # Map priority names to Jira priority
        priority_map = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Lowest",
        }
        jira_priority = priority_map.get(priority.lower(), priority)

        # Build the issue payload
        fields: Dict[str, Any] = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": self.issue_type},
            "priority": {"name": jira_priority},
        }

        if labels:
            fields["labels"] = labels

        if components:
            fields["components"] = [{"name": c} for c in components]

        if incident_id:
            # Add incident ID as a label for tracking
            fields.setdefault("labels", []).append(f"incident:{incident_id}")

        if custom_fields:
            fields.update(custom_fields)

        payload = {"fields": fields}

        try:
            response = await self.client.post("/issue", json=payload)
            response.raise_for_status()
            data = response.json()
            
            ticket_key = data["key"]
            ticket_url = f"{self.url}/browse/{ticket_key}"
            
            logger.info(f"Created Jira ticket: {ticket_key}")
            
            return {
                "id": data["id"],
                "key": ticket_key,
                "url": ticket_url,
                "self": data["self"],
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create Jira ticket: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Jira ticket: {e}")
            raise

    async def add_comment(self, ticket_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an existing ticket."""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        try:
            response = await self.client.post(
                f"/issue/{ticket_key}/comment", json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add comment to {ticket_key}: {e}")
            raise

    async def transition_ticket(
        self, ticket_key: str, transition_name: str
    ) -> Dict[str, Any]:
        """Transition a ticket to a new status."""
        # First, get available transitions
        try:
            transitions_response = await self.client.get(
                f"/issue/{ticket_key}/transitions"
            )
            transitions_response.raise_for_status()
            transitions = transitions_response.json()["transitions"]

            # Find the matching transition
            transition_id = None
            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break

            if not transition_id:
                available = [t["name"] for t in transitions]
                raise ValueError(
                    f"Transition '{transition_name}' not found. Available: {available}"
                )

            # Perform the transition
            response = await self.client.post(
                f"/issue/{ticket_key}/transitions",
                json={"transition": {"id": transition_id}},
            )
            response.raise_for_status()
            
            logger.info(f"Transitioned {ticket_key} to {transition_name}")
            return {"status": "transitioned", "key": ticket_key, "to": transition_name}
        except Exception as e:
            logger.error(f"Failed to transition {ticket_key}: {e}")
            raise

    async def link_incident(
        self, ticket_key: str, incident_url: str, incident_id: str
    ) -> Dict[str, Any]:
        """Add a web link to the incident in the ticket."""
        payload = {
            "object": {
                "url": incident_url,
                "title": f"Incident {incident_id}",
            }
        }

        try:
            response = await self.client.post(
                f"/issue/{ticket_key}/remotelink", json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to link incident to {ticket_key}: {e}")
            raise

    async def get_ticket(self, ticket_key: str) -> Dict[str, Any]:
        """Get ticket details."""
        try:
            response = await self.client.get(f"/issue/{ticket_key}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get ticket {ticket_key}: {e}")
            raise

    async def search_tickets(
        self, jql: str, max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for tickets using JQL."""
        try:
            response = await self.client.get(
                "/search",
                params={"jql": jql, "maxResults": max_results},
            )
            response.raise_for_status()
            return response.json()["issues"]
        except Exception as e:
            logger.error(f"Failed to search tickets: {e}")
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
