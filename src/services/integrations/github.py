"""GitHub integration for issue creation and repository management."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from src.services.integrations.base import BaseIntegration

logger = logging.getLogger(__name__)


class GitHubIntegration(BaseIntegration):
    """GitHub integration for creating issues and managing incidents."""

    def __init__(
        self,
        token: str,
        repository: str,
        api_url: str = "https://api.github.com",
    ):
        self.token = token
        self.repository = repository  # Format: "owner/repo"
        self.api_url = api_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def test_connection(self) -> bool:
        """Test connection to GitHub."""
        try:
            response = await self.client.get("/user")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"GitHub connection test failed: {e}")
            return False

    async def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue for an incident.
        
        Args:
            title: Issue title
            body: Issue body (supports GitHub markdown)
            labels: List of label names to apply
            assignees: List of GitHub usernames to assign
            milestone: Milestone number to associate
            incident_id: Optional incident ID for tracking
            
        Returns:
            Created issue data including number and URL
        """
        # Build issue body with incident reference
        if incident_id:
            body = f"**Incident ID:** `{incident_id}`\n\n{body}"

        payload: Dict[str, Any] = {
            "title": title,
            "body": body,
        }

        if labels:
            payload["labels"] = labels

        if assignees:
            payload["assignees"] = assignees

        if milestone:
            payload["milestone"] = milestone

        try:
            response = await self.client.post(
                f"/repos/{self.repository}/issues", json=payload
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"Created GitHub issue #{data['number']}: {title}")

            return {
                "id": data["id"],
                "number": data["number"],
                "url": data["html_url"],
                "api_url": data["url"],
                "title": data["title"],
                "state": data["state"],
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create GitHub issue: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            raise

    async def add_comment(self, issue_number: int, body: str) -> Dict[str, Any]:
        """Add a comment to an existing issue."""
        try:
            response = await self.client.post(
                f"/repos/{self.repository}/issues/{issue_number}/comments",
                json={"body": body},
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Added comment to GitHub issue #{issue_number}")
            return {
                "id": data["id"],
                "url": data["html_url"],
                "body": data["body"],
            }
        except Exception as e:
            logger.error(f"Failed to add comment to issue #{issue_number}: {e}")
            raise

    async def close_issue(
        self, issue_number: int, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Close an issue with an optional closing comment."""
        try:
            # Add closing comment if provided
            if comment:
                await self.add_comment(issue_number, comment)

            # Close the issue
            response = await self.client.patch(
                f"/repos/{self.repository}/issues/{issue_number}",
                json={"state": "closed"},
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Closed GitHub issue #{issue_number}")
            return {
                "number": data["number"],
                "state": data["state"],
                "url": data["html_url"],
            }
        except Exception as e:
            logger.error(f"Failed to close issue #{issue_number}: {e}")
            raise

    async def add_labels(
        self, issue_number: int, labels: List[str]
    ) -> List[Dict[str, Any]]:
        """Add labels to an issue."""
        try:
            response = await self.client.post(
                f"/repos/{self.repository}/issues/{issue_number}/labels",
                json={"labels": labels},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add labels to issue #{issue_number}: {e}")
            raise

    async def get_issue(self, issue_number: int) -> Dict[str, Any]:
        """Get issue details."""
        try:
            response = await self.client.get(
                f"/repos/{self.repository}/issues/{issue_number}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get issue #{issue_number}: {e}")
            raise

    async def search_issues(
        self, query: str, state: str = "all", max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for issues in the repository."""
        try:
            # Build search query with repo scope
            full_query = f"repo:{self.repository} {query}"
            if state != "all":
                full_query += f" state:{state}"

            response = await self.client.get(
                "/search/issues",
                params={"q": full_query, "per_page": max_results},
            )
            response.raise_for_status()
            return response.json()["items"]
        except Exception as e:
            logger.error(f"Failed to search issues: {e}")
            raise

    async def create_incident_issue(
        self,
        incident_id: str,
        title: str,
        description: str,
        severity: str,
        category: str,
        labels_dict: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a formatted incident issue.
        
        This creates a nicely formatted GitHub issue specifically for incidents.
        """
        # Build markdown body
        body_parts = [
            "## Incident Details",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| **Incident ID** | `{incident_id}` |",
            f"| **Severity** | {self._severity_emoji(severity)} {severity.upper()} |",
            f"| **Category** | {category} |",
            "",
            "## Description",
            "",
            description,
            "",
        ]

        if labels_dict:
            body_parts.extend([
                "## Labels",
                "",
                "| Key | Value |",
                "|-----|-------|",
            ])
            for key, value in labels_dict.items():
                body_parts.append(f"| `{key}` | `{value}` |")
            body_parts.append("")

        body_parts.extend([
            "---",
            "",
            f"*Created by Incident Response Automation*",
        ])

        body = "\n".join(body_parts)

        # Map severity to labels
        labels = ["incident", f"severity:{severity}"]
        if category:
            labels.append(f"category:{category}")

        return await self.create_issue(
            title=f"[{severity.upper()}] {title}",
            body=body,
            labels=labels,
            incident_id=incident_id,
        )

    def _severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level."""
        emojis = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "🔵",
        }
        return emojis.get(severity.lower(), "⚪")

    async def trigger_workflow(
        self,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a GitHub Actions workflow.
        
        Useful for triggering rollback or deployment workflows.
        """
        payload: Dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs

        try:
            response = await self.client.post(
                f"/repos/{self.repository}/actions/workflows/{workflow_id}/dispatches",
                json=payload,
            )
            response.raise_for_status()
            
            logger.info(f"Triggered workflow {workflow_id} on {ref}")
            return {"status": "triggered", "workflow_id": workflow_id, "ref": ref}
        except Exception as e:
            logger.error(f"Failed to trigger workflow {workflow_id}: {e}")
            raise

    async def get_latest_release(self) -> Dict[str, Any]:
        """Get the latest release information."""
        try:
            response = await self.client.get(
                f"/repos/{self.repository}/releases/latest"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get latest release: {e}")
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
