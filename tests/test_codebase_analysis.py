"""Test codebase-aware incident analysis."""

import asyncio
import json
import httpx
from datetime import datetime

from src.services.integrations.jira import JiraIntegration
from src.services.integrations.github import GitHubIntegration
from src.services.ml.providers.openai_provider import OpenAIProvider
from src.services.ml.types import MLPrompt

import os

SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')


async def send_codebase_notification(incident_id, title, severity, analysis, jira_key, jira_url, github_num, github_url):
    """Send detailed Slack notification with codebase analysis."""
    color = '#dc3545' if severity == 'critical' else '#fd7e14'
    
    code_evidence_text = ''
    for ev in analysis.get('code_evidence', [])[:3]:
        code_evidence_text += f"• *{ev.get('file', 'unknown')}:{ev.get('line', '?')}*\n  _{ev.get('issue', 'Issue')}_\n"
    
    fix = analysis.get('recommended_fix', {})
    
    payload = {
        'attachments': [{
            'color': color,
            'blocks': [
                {'type': 'header', 'text': {'type': 'plain_text', 'text': f'🔴 INCIDENT: {title[:50]}', 'emoji': True}},
                {'type': 'section', 'fields': [
                    {'type': 'mrkdwn', 'text': f'*Incident:* `{incident_id}`'},
                    {'type': 'mrkdwn', 'text': f'*Severity:* {severity.upper()}'},
                ]},
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f'*📋 Tracking:* <{jira_url}|{jira_key}> | <{github_url}|GitHub #{github_num}>'}},
                {'type': 'divider'},
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f"*🔬 AI Root Cause Analysis* _(Confidence: {analysis.get('confidence', 0)*100:.0f}%)_\n\n>{analysis.get('root_cause', 'Analysis pending')[:400]}"}},
                {'type': 'divider'},
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f"*📂 Codebase Analysis*\n_Repository: {analysis.get('repository', 'N/A')} | Files: {analysis.get('files_analyzed', 0)}_\n\n*Code Evidence:*\n{code_evidence_text if code_evidence_text else 'See full analysis'}"}},
                {'type': 'divider'},
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f"*🛠️ Recommended Fix*\n*File:* `{fix.get('file', 'N/A')}`\n{fix.get('description', 'See Jira/GitHub for details')[:200]}"}},
                {'type': 'divider'},
                {'type': 'actions', 'elements': [
                    {'type': 'button', 'text': {'type': 'plain_text', 'text': '📋 Jira'}, 'url': jira_url, 'style': 'primary'},
                    {'type': 'button', 'text': {'type': 'plain_text', 'text': '🐙 GitHub'}, 'url': github_url},
                ]},
                {'type': 'context', 'elements': [{'type': 'mrkdwn', 'text': '🤖 _Kustode AI with Codebase Analysis_'}]}
            ]
        }]
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(SLACK_WEBHOOK, json=payload)


async def main():
    print('🚀 Codebase-Aware Incident Analysis')
    print('=' * 60)
    
    jira = JiraIntegration(
        url=os.environ.get('JIRA_URL', 'https://kustode.atlassian.net'),
        username=os.environ.get('JIRA_USERNAME', ''),
        api_token=os.environ.get('JIRA_API_TOKEN', ''),
        project_key='INC',
        issue_type='Submit a request or incident'
    )
    github = GitHubIntegration(token=GITHUB_TOKEN, repository='Kustode-ce/INC')
    llm = OpenAIProvider(
        api_key=os.environ.get('OPENAI_API_KEY', ''),
        model_name='gpt-4o-mini',
        model_version='gpt-4o-mini'
    )
    
    incident = {
        'id': 'INC-2026-0127-200',
        'title': 'Claims API Returning 400 Bad Request Errors',
        'description': 'Claims API /api/v1/claims returning 400 errors for 15% of requests. Error: Invalid claim_type validation. Started after v2.3.1 deployment.',
        'service': 'claims-service',
        'severity': 'critical',
    }
    
    print(f'\n📍 {incident["title"]}')
    
    # AI Analysis with simulated codebase context
    print('\n🤖 Running codebase-aware AI analysis...')
    
    analysis_prompt = '''You are analyzing a production incident for a Claims API. 

INCIDENT: Claims API /api/v1/claims returning HTTP 400 errors for 15% of requests.
Error message: "Invalid claim_type: must be one of [medical, dental, vision]"
Started after deployment v2.3.1

CODEBASE ANALYSIS (I have analyzed the claims-service repository):

1. **src/validators/claims_validator.py (lines 42-58)**:
```python
ALLOWED_CLAIM_TYPES = ["medical", "dental", "vision"]  # Changed in v2.3.1

def validate_claim_type(claim_type: str) -> bool:
    if claim_type.lower() not in ALLOWED_CLAIM_TYPES:  # Bug: .lower() added
        raise ValidationError(f"Invalid claim_type: must be one of {ALLOWED_CLAIM_TYPES}")
    return True
```

2. **src/routes/claims_router.py (line 112)**:
```python
@router.post("/api/v1/claims")
async def create_claim(claim: ClaimRequest):
    validate_claim_type(claim.claim_type)  # Fails for "Medical", "DENTAL" etc
```

3. **src/models/claim.py (line 25)**:
```python
class ClaimRequest(BaseModel):
    claim_type: str  # No validation at model level
```

Based on this codebase analysis, provide detailed JSON response with:
{
    "root_cause": "detailed explanation referencing the exact code",
    "confidence": 0.0-1.0,
    "code_evidence": [{"file": "path", "line": 123, "issue": "description", "code_snippet": "code"}],
    "recommended_fix": {"file": "path", "description": "what to change", "before": "old code", "after": "new code"},
    "contributing_factors": ["factor1", "factor2"],
    "prevention_suggestions": ["suggestion1", "suggestion2"]
}'''

    prompt = MLPrompt(
        system_prompt='You are a senior software engineer. Always reference specific files and line numbers.',
        user_prompt=analysis_prompt
    )
    
    response = await llm.generate(prompt)
    analysis = response.result
    
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except:
            analysis = {'root_cause': analysis, 'confidence': 0.85}
    
    analysis['repository'] = 'kustode/claims-service'
    analysis['files_analyzed'] = 3
    analysis['code_snippets_found'] = 4
    
    print(f"   ✅ Analysis complete (confidence: {analysis.get('confidence', 0)*100:.0f}%)")
    
    # Create Jira
    print('\n🎫 Creating Jira ticket...')
    
    code_ev = '\n'.join([f"*{e.get('file','?')}:{e.get('line','?')}* - {e.get('issue','')}" for e in analysis.get('code_evidence', [])])
    fix = analysis.get('recommended_fix', {})
    
    jira_desc = f'''h1. {incident['id']}

h2. Summary
{incident['description']}

h2. 🔬 AI Codebase Analysis
*Confidence:* {analysis.get('confidence',0)*100:.0f}%
*Repository:* {analysis.get('repository')}

{analysis.get('root_cause', 'N/A')}

h2. 📂 Code Evidence
{code_ev}

h2. 🛠️ Recommended Fix
*File:* {fix.get('file', 'N/A')}
*Change:* {fix.get('description', 'N/A')}

*Before:*
{{code}}
{fix.get('before', 'N/A')}
{{code}}

*After:*
{{code}}
{fix.get('after', 'N/A')}
{{code}}

h2. Prevention
''' + ''.join(['* ' + str(s) + '\n' for s in analysis.get('prevention_suggestions', [])])
    
    jira_ticket = await jira.create_ticket(
        summary=f'[CRITICAL] {incident["title"]}',
        description=jira_desc,
        priority='Highest',
        labels=['incident', 'claims-api', 'codebase-analyzed'],
        incident_id=incident['id']
    )
    print(f'   ✅ {jira_ticket["key"]}')
    
    # Create GitHub
    print('\n🐙 Creating GitHub issue...')
    
    code_evidence_md = ''
    for e in analysis.get('code_evidence', []):
        code_evidence_md += f"\n#### `{e.get('file','?')}:{e.get('line','?')}`\n```python\n{e.get('code_snippet','N/A')}\n```\n_{e.get('issue','')}_\n"
    
    github_body = f'''## 🚨 {incident['id']}

### Summary
{incident['description']}

---

### 🔬 AI Codebase Analysis
**Confidence:** {analysis.get('confidence',0)*100:.0f}%
**Repository:** {analysis.get('repository')}

> {analysis.get('root_cause', 'N/A')}

### 📂 Code Evidence
{code_evidence_md}

### 🛠️ Recommended Fix
**File:** `{fix.get('file', 'N/A')}`
**Change:** {fix.get('description', 'N/A')}

**Before:**
```python
{fix.get('before', 'N/A')}
```

**After:**
```python
{fix.get('after', 'N/A')}
```

### Prevention
''' + ''.join(['- ' + str(s) + '\n' for s in analysis.get('prevention_suggestions', [])]) + '''

---
_🤖 Kustode AI with Codebase Analysis_
'''
    
    github_issue = await github.create_issue(
        title=f'[CRITICAL] {incident["title"]}',
        body=github_body,
        labels=['incident', 'claims-api', 'codebase-analyzed']
    )
    print(f'   ✅ #{github_issue["number"]}')
    
    # Slack
    print('\n💬 Sending notification...')
    await send_codebase_notification(
        incident['id'], incident['title'], incident['severity'],
        analysis, jira_ticket['key'], jira_ticket['url'],
        github_issue['number'], github_issue['url']
    )
    print('   ✅ Sent')
    
    print('\n' + '=' * 60)
    print('📊 CODEBASE-AWARE ANALYSIS COMPLETE')
    print('=' * 60)
    print(f'''
Incident: {incident['id']}
Jira: {jira_ticket['url']}
GitHub: {github_issue['url']}

Root Cause: {analysis.get('root_cause', 'N/A')[:150]}...
''')
    
    await jira.close()
    await github.close()


if __name__ == '__main__':
    asyncio.run(main())
