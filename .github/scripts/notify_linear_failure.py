"""Create or update a Linear issue when a GitHub Actions workflow fails."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

LINEAR_API_URL = os.environ.get("LINEAR_API_URL", "https://api.linear.app/graphql")
KST = timezone(timedelta(hours=9))

ISSUES_QUERY = """
query OpenCiIssues($filter: IssueFilter!, $first: Int!) {
  issues(filter: $filter, first: $first) {
    nodes {
      id
      identifier
      title
      url
    }
  }
}
"""

COMMENT_MUTATION = """
mutation CommentCreate($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment {
      id
    }
  }
}
"""

ISSUE_CREATE_MUTATION = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      url
    }
  }
}
"""


def graphql(query: str, variables: dict | None = None) -> dict:
    api_key = os.environ["LINEAR_API_KEY"]
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "User-Agent": "ollama-advisor-ci-notifier/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    if data.get("errors"):
        raise RuntimeError(f"Linear API error: {data['errors']}")
    return data["data"]


def build_title(workflow_name: str, repository: str) -> str:
    return f"[CI] {workflow_name} failed — {repository}"


def build_description() -> str:
    workflow_name = os.environ.get("WORKFLOW_NAME", "unknown workflow")
    workflow_run_url = os.environ.get("WORKFLOW_RUN_URL", "")
    workflow_run_id = os.environ.get("WORKFLOW_RUN_ID", "")
    repository = os.environ.get("REPOSITORY", "")
    branch = os.environ.get("BRANCH", "")
    commit_sha = os.environ.get("COMMIT_SHA", "")
    event_name = os.environ.get("EVENT_NAME", "")
    actor = os.environ.get("ACTOR", "")
    timestamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    lines = [
        "GitHub Actions workflow failed.",
        "",
        f"- Workflow: `{workflow_name}`",
        f"- Repository: `{repository}`",
        f"- Branch: `{branch}`",
        f"- Commit: `{commit_sha}`",
        f"- Event: `{event_name}`",
        f"- Triggered by: `{actor}`",
        f"- Run ID: `{workflow_run_id}`",
        f"- Detected at: `{timestamp}`",
    ]
    if workflow_run_url:
        lines.extend(["", f"[View workflow run]({workflow_run_url})"])
    return "\n".join(lines)


def find_open_issue(team_id: str, title: str) -> dict | None:
    data = graphql(
        ISSUES_QUERY,
        {
            "first": 5,
            "filter": {
                "team": {"id": {"eq": team_id}},
                "title": {"eq": title},
                "state": {"type": {"nin": ["completed", "canceled"]}},
            },
        },
    )
    nodes = data["issues"]["nodes"]
    return nodes[0] if nodes else None


def add_comment(issue_id: str, body: str) -> None:
    data = graphql(COMMENT_MUTATION, {"input": {"issueId": issue_id, "body": body}})
    if not data["commentCreate"]["success"]:
        raise RuntimeError("Failed to add Linear comment")


def create_issue(team_id: str, title: str, description: str) -> dict:
    issue_input: dict = {
        "teamId": team_id,
        "title": title,
        "description": description,
        "priority": 2,
    }
    label_ids = os.environ.get("LINEAR_LABEL_IDS", "").strip()
    if label_ids:
        issue_input["labelIds"] = [label_id.strip() for label_id in label_ids.split(",") if label_id.strip()]

    data = graphql(ISSUE_CREATE_MUTATION, {"input": issue_input})
    result = data["issueCreate"]
    if not result["success"]:
        raise RuntimeError("Failed to create Linear issue")
    return result["issue"]


def main() -> int:
    api_key = os.environ.get("LINEAR_API_KEY", "").strip()
    team_id = os.environ.get("LINEAR_TEAM_ID", "").strip()
    workflow_name = os.environ.get("WORKFLOW_NAME", "").strip()

    if not api_key or not team_id:
        print("LINEAR_API_KEY or LINEAR_TEAM_ID not configured; skipping Linear notification.")
        return 0

    if not workflow_name:
        print("WORKFLOW_NAME is required; skipping Linear notification.")
        return 0

    title = build_title(workflow_name, os.environ.get("REPOSITORY", "unknown"))
    description = build_description()

    if os.environ.get("DRY_RUN") == "1":
        print(f"DRY RUN: would notify Linear about failure")
        print(f"title={title}")
        print(description)
        return 0

    try:
        existing = find_open_issue(team_id, title)
        if existing:
            add_comment(
                existing["id"],
                f"Workflow failed again.\n\n{description}",
            )
            print(f"Updated existing Linear issue: {existing['identifier']} ({existing['url']})")
            return 0

        issue = create_issue(team_id, title, description)
        print(f"Created Linear issue: {issue['identifier']} ({issue['url']})")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"Linear HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
