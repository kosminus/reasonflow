"""Seed workflows derived from the examples/ folder."""

from __future__ import annotations


CODE_REVIEWER = {
    "name": "code_reviewer",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "get_diff",
                    "code": (
                        "import subprocess\n"
                        "repo = state.get(\"repo_path\", \".\")\n"
                        "\n"
                        "# Try staged first, fall back to unstaged\n"
                        "result = subprocess.run(\n"
                        "    [\"git\", \"-C\", repo, \"diff\", \"--cached\"],\n"
                        "    capture_output=True,\n"
                        "    text=True,\n"
                        ")\n"
                        "\n"
                        "diff = result.stdout.strip()\n"
                        "diff_type = \"staged\"\n"
                        "\n"
                        "if not diff:\n"
                        "    result = subprocess.run(\n"
                        "        [\"git\", \"-C\", repo, \"diff\"],\n"
                        "        capture_output=True,\n"
                        "        text=True,\n"
                        "    )\n"
                        "    diff = result.stdout.strip()\n"
                        "    diff_type = \"unstaged\"\n"
                        "\n"
                        "if not diff:\n"
                        "    result = subprocess.run(\n"
                        "        [\"git\", \"-C\", repo, \"diff\", \"HEAD~1\"],\n"
                        "        capture_output=True,\n"
                        "        text=True,\n"
                        "    )\n"
                        "    diff = result.stdout.strip()\n"
                        "    diff_type = \"last commit\"\n"
                        "\n"
                        "# Truncate very large diffs\n"
                        "max_chars = 8000\n"
                        "truncated = len(diff) > max_chars\n"
                        "if truncated:\n"
                        "    diff = diff[:max_chars] + \"\\n... (truncated)\"\n"
                        "\n"
                        "return {\"diff\": diff, \"diff_type\": diff_type, \"truncated\": truncated}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "llm",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "review_code",
                    "model": "claude-sonnet",
                    "prompt": (
                        "You are a senior code reviewer. Review this diff carefully.\n"
                        "\n"
                        "Diff type: {diff_type}\n"
                        "\n"
                        "```diff\n"
                        "{diff}\n"
                        "```\n"
                        "\n"
                        "Provide a thorough review covering:\n"
                        "1. Potential bugs or logic errors\n"
                        "2. Security concerns\n"
                        "3. Performance issues\n"
                        "4. Style and readability\n"
                        "5. Suggestions for improvement\n"
                        "\n"
                        "Return as JSON with keys:\n"
                        "- \"severity\" (one of: \"clean\", \"minor\", \"major\", \"critical\")\n"
                        "- \"issues\" (list of {{\"category\": str, \"description\": str, \"line_hint\": str}})\n"
                        "- \"summary\" (one sentence overall assessment)"
                    ),
                },
            },
            {
                "id": "n3",
                "type": "code",
                "position": {"x": 80, "y": 440},
                "data": {
                    "name": "save_review",
                    "code": (
                        "from datetime import datetime\n"
                        "from pathlib import Path\n"
                        "timestamp = datetime.now().strftime(\"%Y-%m-%d_%H-%M-%S\")\n"
                        "review_dir = Path.home() / \".reasonflow\" / \"reviews\"\n"
                        "review_dir.mkdir(parents=True, exist_ok=True)\n"
                        "review_path = review_dir / f\"code_review_{timestamp}.txt\"\n"
                        "\n"
                        "lines = [\n"
                        "    f\"Code Review - {timestamp}\",\n"
                        "    f\"Diff type: {state.get('diff_type', 'unknown')}\",\n"
                        "    f\"Severity: {state.get('severity', 'unknown')}\",\n"
                        "    \"\",\n"
                        "    f\"Summary: {state.get('summary', 'N/A')}\",\n"
                        "    \"\",\n"
                        "    \"Issues:\",\n"
                        "]\n"
                        "\n"
                        "for issue in state.get(\"issues\", []):\n"
                        "    lines.append(f\"  [{issue.get('category', '?')}] {issue.get('description', '')}\")\n"
                        "    if issue.get(\"line_hint\"):\n"
                        "        lines.append(f\"    Near: {issue['line_hint']}\")\n"
                        "\n"
                        "review = \"\\n\".join(lines) + \"\\n\"\n"
                        "review_path.write_text(review)\n"
                        "\n"
                        "return {\"review_text\": review, \"review_path\": str(review_path)}"
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ],
    },
}


CSV_ANALYZER = {
    "name": "csv_analyzer",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "read_csv",
                    "code": (
                        "import csv\n"
                        "from pathlib import Path\n"
                        "csv_path = state.get(\"csv_path\", \"data.csv\")\n"
                        "path = Path(csv_path)\n"
                        "\n"
                        "if not path.exists():\n"
                        "    import random\n"
                        "    random.seed(42)\n"
                        "    rows = []\n"
                        "    products = [\"Widget A\", \"Widget B\", \"Gadget X\", \"Gadget Y\"]\n"
                        "    regions = [\"North\", \"South\", \"East\", \"West\"]\n"
                        "    for month in range(1, 13):\n"
                        "        for product in products:\n"
                        "            for region in regions:\n"
                        "                rows.append({\n"
                        "                    \"month\": str(month),\n"
                        "                    \"product\": product,\n"
                        "                    \"region\": region,\n"
                        "                    \"units\": str(random.randint(50, 500)),\n"
                        "                    \"revenue\": str(round(random.uniform(1000, 25000), 2)),\n"
                        "                })\n"
                        "    return {\n"
                        "        \"headers\": [\"month\", \"product\", \"region\", \"units\", \"revenue\"],\n"
                        "        \"row_count\": len(rows),\n"
                        "        \"rows\": rows,\n"
                        "        \"csv_path\": \"(generated sample data)\",\n"
                        "    }\n"
                        "\n"
                        "with open(path) as f:\n"
                        "    reader = csv.DictReader(f)\n"
                        "    rows = list(reader)\n"
                        "\n"
                        "return {\n"
                        "    \"headers\": list(rows[0].keys()) if rows else [],\n"
                        "    \"row_count\": len(rows),\n"
                        "    \"rows\": rows,\n"
                        "    \"csv_path\": str(path),\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "code",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "compute_stats",
                    "code": (
                        "import statistics\n"
                        "rows = state.get(\"rows\", [])\n"
                        "headers = state.get(\"headers\", [])\n"
                        "\n"
                        "if not rows:\n"
                        "    return {\"stats\": {}, \"sample_rows\": []}\n"
                        "\n"
                        "stats = {}\n"
                        "for col in headers:\n"
                        "    values = []\n"
                        "    for row in rows:\n"
                        "        try:\n"
                        "            values.append(float(row[col]))\n"
                        "        except (ValueError, KeyError):\n"
                        "            break\n"
                        "    else:\n"
                        "        if values:\n"
                        "            stats[col] = {\n"
                        "                \"min\": round(min(values), 2),\n"
                        "                \"max\": round(max(values), 2),\n"
                        "                \"mean\": round(statistics.mean(values), 2),\n"
                        "                \"median\": round(statistics.median(values), 2),\n"
                        "                \"stdev\": round(statistics.stdev(values), 2) if len(values) > 1 else 0,\n"
                        "                \"sum\": round(sum(values), 2),\n"
                        "            }\n"
                        "\n"
                        "sample = rows[:5]\n"
                        "\n"
                        "return {\"stats\": stats, \"sample_rows\": sample}"
                    ),
                },
            },
            {
                "id": "n3",
                "type": "llm",
                "position": {"x": 80, "y": 440},
                "data": {
                    "name": "analyze_data",
                    "model": "claude-haiku",
                    "prompt": (
                        "You are a data analyst. Analyze this CSV dataset.\n"
                        "\n"
                        "File: {csv_path}\n"
                        "Total rows: {row_count}\n"
                        "Columns: {headers}\n"
                        "\n"
                        "Statistics:\n"
                        "{stats}\n"
                        "\n"
                        "Sample rows:\n"
                        "{sample_rows}\n"
                        "\n"
                        "Provide:\n"
                        "1. A brief description of the dataset\n"
                        "2. Key patterns or trends in the numbers\n"
                        "3. Any anomalies or notable observations\n"
                        "4. One actionable recommendation\n"
                        "\n"
                        "Return as JSON with keys: \"description\", \"patterns\" (list), \"anomalies\" (list), \"recommendation\"."
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ],
    },
}


EMAIL_DRAFTER = {
    "name": "email_drafter",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "prepare_input",
                    "code": (
                        "bullets = state.get(\"bullets\", [\n"
                        "    \"Q1 revenue up 23% YoY\",\n"
                        "    \"Shipped 3 major features: real-time collab, API v2, mobile app\",\n"
                        "    \"Customer churn dropped from 5.2% to 3.8%\",\n"
                        "    \"Hired 12 new engineers, 4 still in pipeline\",\n"
                        "    \"Infrastructure costs reduced 15% via migration to ARM instances\",\n"
                        "    \"Next quarter focus: enterprise tier launch and SOC2 certification\",\n"
                        "])\n"
                        "\n"
                        "return {\n"
                        "    \"bullets\": bullets,\n"
                        "    \"recipient\": state.get(\"recipient\", \"Team\"),\n"
                        "    \"subject\": state.get(\"subject\", \"Update\"),\n"
                        "    \"tone\": state.get(\"tone\", \"professional but warm\"),\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "llm",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "draft_email",
                    "model": "claude-haiku",
                    "prompt": (
                        "You are a professional email writer. Draft an email from these bullet points.\n"
                        "\n"
                        "To: {recipient}\n"
                        "Subject: {subject}\n"
                        "Tone: {tone}\n"
                        "\n"
                        "Key points:\n"
                        "{bullets}\n"
                        "\n"
                        "Write a well-structured email that:\n"
                        "- Opens with a brief greeting\n"
                        "- Covers all bullet points naturally (don't just list them)\n"
                        "- Closes with a forward-looking statement\n"
                        "- Keeps it under 250 words\n"
                        "\n"
                        "Return as JSON with keys: \"subject_line\", \"body\", \"word_count\"."
                    ),
                },
            },
            {
                "id": "n3",
                "type": "llm",
                "position": {"x": 80, "y": 440},
                "data": {
                    "name": "review_email",
                    "model": "claude-sonnet",
                    "prompt": (
                        "You are an executive communications coach. Review this draft email.\n"
                        "\n"
                        "Subject: {subject_line}\n"
                        "\n"
                        "{body}\n"
                        "\n"
                        "Evaluate on:\n"
                        "1. Clarity and conciseness\n"
                        "2. Tone appropriateness\n"
                        "3. Missing information or unclear points\n"
                        "4. Grammar and style\n"
                        "\n"
                        "If improvements are needed, provide a revised version.\n"
                        "Return as JSON with keys:\n"
                        "- \"score\" (1-10)\n"
                        "- \"feedback\" (list of specific suggestions)\n"
                        "- \"revised_body\" (improved version, or null if the draft is good)"
                    ),
                },
            },
            {
                "id": "n4",
                "type": "code",
                "position": {"x": 80, "y": 620},
                "data": {
                    "name": "save_draft",
                    "code": (
                        "from datetime import datetime\n"
                        "from pathlib import Path\n"
                        "timestamp = datetime.now().strftime(\"%Y-%m-%d_%H-%M-%S\")\n"
                        "draft_dir = Path.home() / \".reasonflow\" / \"drafts\"\n"
                        "draft_dir.mkdir(parents=True, exist_ok=True)\n"
                        "draft_path = draft_dir / f\"email_{timestamp}.txt\"\n"
                        "\n"
                        "body = state.get(\"revised_body\") or state.get(\"body\", \"\")\n"
                        "subject = state.get(\"subject_line\", state.get(\"subject\", \"\"))\n"
                        "\n"
                        "content = f\"Subject: {subject}\\nTo: {state.get('recipient', '')}\\n\\n{body}\\n\"\n"
                        "draft_path.write_text(content)\n"
                        "\n"
                        "return {\n"
                        "    \"final_body\": body,\n"
                        "    \"draft_path\": str(draft_path),\n"
                        "    \"was_revised\": state.get(\"revised_body\") is not None,\n"
                        "}"
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
        ],
    },
}


GIT_CHANGELOG = {
    "name": "git_changelog",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "get_commits",
                    "code": (
                        "import subprocess\n"
                        "repo = state.get(\"repo_path\", \".\")\n"
                        "count = state.get(\"commit_count\", 20)\n"
                        "\n"
                        "result = subprocess.run(\n"
                        "    [\"git\", \"-C\", repo, \"log\", f\"-{count}\", \"--pretty=format:%h|%an|%s|%ad\", \"--date=short\"],\n"
                        "    capture_output=True,\n"
                        "    text=True,\n"
                        ")\n"
                        "\n"
                        "if result.returncode != 0:\n"
                        "    return {\"commits\": [], \"error\": result.stderr.strip()}\n"
                        "\n"
                        "commits = []\n"
                        "for line in result.stdout.strip().splitlines():\n"
                        "    parts = line.split(\"|\", 3)\n"
                        "    if len(parts) == 4:\n"
                        "        commits.append({\n"
                        "            \"hash\": parts[0],\n"
                        "            \"author\": parts[1],\n"
                        "            \"message\": parts[2],\n"
                        "            \"date\": parts[3],\n"
                        "        })\n"
                        "\n"
                        "return {\"commits\": commits, \"commit_count\": len(commits)}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "code",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "get_tags",
                    "code": (
                        "import subprocess\n"
                        "repo = state.get(\"repo_path\", \".\")\n"
                        "\n"
                        "result = subprocess.run(\n"
                        "    [\"git\", \"-C\", repo, \"tag\", \"--sort=-creatordate\", \"-l\"],\n"
                        "    capture_output=True,\n"
                        "    text=True,\n"
                        ")\n"
                        "\n"
                        "tags = result.stdout.strip().splitlines()[:5] if result.returncode == 0 else []\n"
                        "return {\"recent_tags\": tags}"
                    ),
                },
            },
            {
                "id": "n3",
                "type": "llm",
                "position": {"x": 80, "y": 440},
                "data": {
                    "name": "generate_changelog",
                    "model": "claude-haiku",
                    "prompt": (
                        "You are a technical writer. Generate clean release notes from these git commits.\n"
                        "\n"
                        "Commits:\n"
                        "{commits}\n"
                        "\n"
                        "Recent tags: {recent_tags}\n"
                        "\n"
                        "Group commits by category (Features, Fixes, Refactoring, Docs, Other).\n"
                        "Use clear, user-facing language. Skip merge commits.\n"
                        "Return as JSON with keys: \"version\" (suggested), \"date\", \"sections\" (dict of category -> list of changes)."
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ],
    },
}


LOG_ANALYZER = {
    "name": "log_analyzer",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "read_logs",
                    "code": (
                        "from pathlib import Path\n"
                        "log_path = state.get(\"log_path\", \"/var/log/system.log\")\n"
                        "max_lines = state.get(\"max_lines\", 500)\n"
                        "path = Path(log_path)\n"
                        "\n"
                        "if not path.exists():\n"
                        "    logs = [\n"
                        "        \"2025-03-05 10:01:23 INFO  [main] Application started successfully\",\n"
                        "        \"2025-03-05 10:01:24 INFO  [db] Connected to PostgreSQL at localhost:5432\",\n"
                        "        \"2025-03-05 10:02:15 WARN  [http] Slow query: GET /api/users took 2340ms\",\n"
                        "        \"2025-03-05 10:02:18 ERROR [http] Connection timeout: upstream server api.example.com:8080\",\n"
                        "        \"2025-03-05 10:03:01 INFO  [worker] Processing batch job #4521\",\n"
                        "        \"2025-03-05 10:03:45 ERROR [db] Deadlock detected in transaction 8832\",\n"
                        "        \"2025-03-05 10:03:45 ERROR [db] Rolling back transaction 8832\",\n"
                        "        \"2025-03-05 10:04:12 WARN  [mem] Heap usage at 78% (1.2GB / 1.5GB)\",\n"
                        "        \"2025-03-05 10:05:00 INFO  [scheduler] Cron job 'cleanup' started\",\n"
                        "        \"2025-03-05 10:05:33 ERROR [http] 500 Internal Server Error: /api/orders/create\",\n"
                        "        \"2025-03-05 10:05:33 ERROR [http] NullPointerException at OrderService.java:142\",\n"
                        "        \"2025-03-05 10:06:01 WARN  [auth] Failed login attempt for user 'admin' from 192.168.1.50\",\n"
                        "        \"2025-03-05 10:06:02 WARN  [auth] Failed login attempt for user 'admin' from 192.168.1.50\",\n"
                        "        \"2025-03-05 10:06:03 WARN  [auth] Failed login attempt for user 'admin' from 192.168.1.50\",\n"
                        "        \"2025-03-05 10:07:15 ERROR [disk] Write failed: /data/cache - No space left on device\",\n"
                        "        \"2025-03-05 10:08:00 INFO  [http] Health check OK - uptime 6h 23m\",\n"
                        "    ]\n"
                        "    return {\n"
                        "        \"log_lines\": logs,\n"
                        "        \"total_lines\": len(logs),\n"
                        "        \"lines_read\": len(logs),\n"
                        "        \"log_source\": \"(generated sample data)\",\n"
                        "    }\n"
                        "\n"
                        "lines = path.read_text().splitlines()\n"
                        "recent = lines[-max_lines:] if len(lines) > max_lines else lines\n"
                        "\n"
                        "return {\n"
                        "    \"log_lines\": recent,\n"
                        "    \"total_lines\": len(lines),\n"
                        "    \"lines_read\": len(recent),\n"
                        "    \"log_source\": str(path),\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "code",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "extract_errors",
                    "code": (
                        "lines = state.get(\"log_lines\", [])\n"
                        "\n"
                        "errors = []\n"
                        "warnings = []\n"
                        "for line in lines:\n"
                        "    lower = line.lower()\n"
                        "    if \"error\" in lower or \"exception\" in lower or \"fatal\" in lower:\n"
                        "        errors.append(line)\n"
                        "    elif \"warn\" in lower:\n"
                        "        warnings.append(line)\n"
                        "\n"
                        "unique_errors = list(dict.fromkeys(errors))\n"
                        "\n"
                        "return {\n"
                        "    \"errors\": unique_errors,\n"
                        "    \"warnings\": warnings,\n"
                        "    \"error_count\": len(errors),\n"
                        "    \"warning_count\": len(warnings),\n"
                        "    \"unique_error_count\": len(unique_errors),\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n3",
                "type": "llm",
                "position": {"x": 80, "y": 440},
                "data": {
                    "name": "categorize_errors",
                    "model": "claude-haiku",
                    "prompt": (
                        "You are a DevOps engineer analyzing application logs.\n"
                        "\n"
                        "Log source: {log_source}\n"
                        "Total lines: {total_lines}\n"
                        "Errors found: {error_count} ({unique_error_count} unique)\n"
                        "Warnings found: {warning_count}\n"
                        "\n"
                        "Errors:\n"
                        "{errors}\n"
                        "\n"
                        "Warnings:\n"
                        "{warnings}\n"
                        "\n"
                        "Categorize each error by:\n"
                        "1. Root cause category (network, database, disk, application, security)\n"
                        "2. Severity (critical, high, medium, low)\n"
                        "3. Recommended action\n"
                        "\n"
                        "Return as JSON with keys:\n"
                        "- \"categories\" (list of {{\"error\": str, \"category\": str, \"severity\": str, \"action\": str}})\n"
                        "- \"most_urgent\" (string - the single most important issue to fix first)\n"
                        "- \"overall_health\" (one of: \"healthy\", \"degraded\", \"critical\")"
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ],
    },
}


MULTI_MODEL_DEBATE = {
    "name": "multi_model_debate",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 280, "y": 80},
                "data": {
                    "name": "prepare",
                    "code": (
                        "return {'question': state.get('question', "
                        "'Should companies adopt AI coding assistants?')}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "llm",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "perspective_a",
                    "model": "claude-haiku",
                    "prompt": (
                        "You are a pragmatic CTO who focuses on developer productivity and ROI.\n"
                        "\n"
                        "Question: {question}\n"
                        "\n"
                        "Argue your position in 3-4 sentences. Be specific with examples."
                    ),
                },
            },
            {
                "id": "n3",
                "type": "llm",
                "position": {"x": 280, "y": 260},
                "data": {
                    "name": "perspective_b",
                    "model": "gpt-4o-mini",
                    "prompt": (
                        "You are a security-focused engineering lead concerned about code quality and IP risks.\n"
                        "\n"
                        "Question: {question}\n"
                        "\n"
                        "Argue your position in 3-4 sentences. Be specific with examples."
                    ),
                },
            },
            {
                "id": "n4",
                "type": "llm",
                "position": {"x": 480, "y": 260},
                "data": {
                    "name": "perspective_c",
                    "model": "claude-sonnet",
                    "prompt": (
                        "You are a senior developer who cares about craft, learning, and long-term skill development.\n"
                        "\n"
                        "Question: {question}\n"
                        "\n"
                        "Argue your position in 3-4 sentences. Be specific with examples."
                    ),
                },
            },
            {
                "id": "n5",
                "type": "llm",
                "position": {"x": 280, "y": 460},
                "data": {
                    "name": "judge",
                    "model": "claude-sonnet",
                    "prompt": (
                        "You are a balanced moderator. Three experts debated this question:\n"
                        "\n"
                        "Question: {question}\n"
                        "\n"
                        "Perspective A (CTO - productivity focus):\n"
                        "{perspective_a}\n"
                        "\n"
                        "Perspective B (Security lead - risk focus):\n"
                        "{perspective_b}\n"
                        "\n"
                        "Perspective C (Senior dev - craft focus):\n"
                        "{perspective_c}\n"
                        "\n"
                        "Synthesize their arguments into a balanced verdict:\n"
                        "1. Where they agree\n"
                        "2. Key tensions between perspectives\n"
                        "3. Your recommended approach\n"
                        "\n"
                        "Return as JSON with keys: \"consensus\" (list), \"tensions\" (list), \"verdict\" (string)."
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n1", "target": "n3"},
            {"source": "n1", "target": "n4"},
            {"source": "n2", "target": "n5"},
            {"source": "n3", "target": "n5"},
            {"source": "n4", "target": "n5"},
        ],
    },
}


PROCESS_MANAGER = {
    "name": "process_manager",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "list_processes",
                    "code": (
                        "import subprocess\n"
                        "result = subprocess.run([\"ps\", \"aux\"], capture_output=True, text=True)\n"
                        "return {\n"
                        "    \"ps_output\": result.stdout,\n"
                        "    \"ps_line_count\": len(result.stdout.strip().splitlines()),\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "code",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "find_whatsapp",
                    "code": (
                        "lines = state.get(\"ps_output\", \"\").splitlines()\n"
                        "matches = [l for l in lines if \"whatsapp\" in l.lower()]\n"
                        "pids = []\n"
                        "for line in matches:\n"
                        "    parts = line.split()\n"
                        "    if len(parts) >= 2:\n"
                        "        pids.append(parts[1])\n"
                        "return {\n"
                        "    \"whatsapp_lines\": matches,\n"
                        "    \"whatsapp_pids\": pids,\n"
                        "    \"whatsapp_found\": len(pids) > 0,\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n3",
                "type": "code",
                "position": {"x": 80, "y": 440},
                "data": {
                    "name": "kill_whatsapp",
                    "code": (
                        "import subprocess\n"
                        "pids = state.get(\"whatsapp_pids\", [])\n"
                        "if not pids:\n"
                        "    return {\"kill_results\": [], \"action\": \"skipped - WhatsApp not running\"}\n"
                        "\n"
                        "results = []\n"
                        "for pid in pids:\n"
                        "    proc = subprocess.run([\"kill\", pid], capture_output=True, text=True)\n"
                        "    results.append({\n"
                        "        \"pid\": pid,\n"
                        "        \"success\": proc.returncode == 0,\n"
                        "        \"error\": proc.stderr.strip() if proc.returncode != 0 else None,\n"
                        "    })\n"
                        "killed = [r[\"pid\"] for r in results if r[\"success\"]]\n"
                        "return {\n"
                        "    \"kill_results\": results,\n"
                        "    \"action\": f\"killed {len(killed)} process(es)\" if killed else \"kill failed\",\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n4",
                "type": "code",
                "position": {"x": 80, "y": 620},
                "data": {
                    "name": "save_report",
                    "code": (
                        "from datetime import datetime\n"
                        "from pathlib import Path\n"
                        "timestamp = datetime.now().strftime(\"%Y-%m-%d_%H-%M-%S\")\n"
                        "report_dir = Path.home() / \".reasonflow\" / \"reports\"\n"
                        "report_dir.mkdir(parents=True, exist_ok=True)\n"
                        "report_path = report_dir / f\"process_manager_{timestamp}.txt\"\n"
                        "\n"
                        "lines = [\n"
                        "    f\"Process Manager Report - {timestamp}\",\n"
                        "    \"=\" * 50,\n"
                        "    \"\",\n"
                        "    f\"Total processes scanned: {state.get('ps_line_count', 0)}\",\n"
                        "    f\"WhatsApp found: {state.get('whatsapp_found', False)}\",\n"
                        "    f\"WhatsApp PIDs: {state.get('whatsapp_pids', [])}\",\n"
                        "    \"\",\n"
                        "    f\"Action taken: {state.get('action', 'none')}\",\n"
                        "    \"\",\n"
                        "]\n"
                        "\n"
                        "for result in state.get(\"kill_results\", []):\n"
                        "    status = \"killed\" if result[\"success\"] else f\"failed: {result['error']}\"\n"
                        "    lines.append(f\"  PID {result['pid']}: {status}\")\n"
                        "\n"
                        "if state.get(\"whatsapp_lines\"):\n"
                        "    lines += [\"\", \"Matched process lines:\", \"\"]\n"
                        "    lines += [f\"  {l}\" for l in state[\"whatsapp_lines\"]]\n"
                        "\n"
                        "report = \"\\n\".join(lines) + \"\\n\"\n"
                        "report_path.write_text(report)\n"
                        "\n"
                        "return {\"report\": report, \"report_path\": str(report_path)}"
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
        ],
    },
}


RESEARCH_PIPELINE = {
    "name": "research_pipeline",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 280, "y": 80},
                "data": {
                    "name": "prepare",
                    "code": (
                        "return {'topic': state.get('topic', 'AI safety')}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "code",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "research_web",
                    "code": (
                        "topic = state.get(\"topic\", \"unknown\")\n"
                        "return {\n"
                        "    \"web_results\": [\n"
                        "        f\"Web result 1 about {topic}: Latest developments...\",\n"
                        "        f\"Web result 2 about {topic}: Expert opinions...\",\n"
                        "        f\"Web result 3 about {topic}: Recent papers...\",\n"
                        "    ]\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n3",
                "type": "code",
                "position": {"x": 280, "y": 260},
                "data": {
                    "name": "research_internal",
                    "code": (
                        "topic = state.get(\"topic\", \"unknown\")\n"
                        "return {\n"
                        "    \"db_results\": [\n"
                        "        f\"Internal doc 1: Company policy on {topic}\",\n"
                        "        f\"Internal doc 2: Previous analysis of {topic}\",\n"
                        "    ]\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n4",
                "type": "code",
                "position": {"x": 480, "y": 260},
                "data": {
                    "name": "research_code",
                    "code": (
                        "topic = state.get(\"topic\", \"unknown\")\n"
                        "return {\n"
                        "    \"code_results\": [\n"
                        "        f\"repo/src/main.py: Implementation related to {topic}\",\n"
                        "        f\"repo/tests/test_core.py: Tests for {topic} features\",\n"
                        "    ]\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n5",
                "type": "llm",
                "position": {"x": 280, "y": 460},
                "data": {
                    "name": "synthesize",
                    "model": "gpt-5.2",
                    "prompt": (
                        "You are a research analyst. Synthesize findings from multiple sources\n"
                        "into a comprehensive report.\n"
                        "\n"
                        "Web research: {web_results}\n"
                        "Internal documents: {db_results}\n"
                        "Code references: {code_results}\n"
                        "\n"
                        "Provide a structured summary with key findings and recommendations.\n"
                        "Return as JSON with keys: \"summary\", \"key_findings\" (list), \"recommendations\" (list)."
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n1", "target": "n3"},
            {"source": "n1", "target": "n4"},
            {"source": "n2", "target": "n5"},
            {"source": "n3", "target": "n5"},
            {"source": "n4", "target": "n5"},
        ],
    },
}


RUN_AND_ANALYZE = {
    "name": "run_and_analyze",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "run_script",
                    "code": (
                        "import subprocess\n"
                        "from pathlib import Path\n"
                        "script = Path.home() / \"claude-workspace\" / \"reasonflow\" / \"examples\" / \"another_code_example.py\"\n"
                        "result = subprocess.run(\n"
                        "    [\"python\", str(script)],\n"
                        "    capture_output=True,\n"
                        "    text=True,\n"
                        ")\n"
                        "return {\n"
                        "    \"stdout\": result.stdout,\n"
                        "    \"stderr\": result.stderr,\n"
                        "    \"exit_code\": result.returncode,\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "llm",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "analyze_output",
                    "model": "gpt-5.2",
                    "prompt": (
                        "You are a business analyst. Analyze the script output below and provide:\n"
                        "1. A brief summary of the data\n"
                        "2. Key insights or trends\n"
                        "3. One actionable recommendation\n"
                        "\n"
                        "Script output:\n"
                        "{stdout}\n"
                        "\n"
                        "Keep your response concise (3-5 sentences)."
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
        ],
    },
}


WEB_SCRAPER_SUMMARIZER = {
    "name": "web_scraper_summarizer",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "fetch_page",
                    "code": (
                        "import re\n"
                        "import httpx\n"
                        "\n"
                        "url = state.get(\"url\", \"https://example.com\")\n"
                        "\n"
                        "response = httpx.get(url, follow_redirects=True, timeout=15)\n"
                        "response.raise_for_status()\n"
                        "\n"
                        "html = response.text\n"
                        "\n"
                        "text = re.sub(r\"<script[^>]*>.*?</script>\", \"\", html, flags=re.DOTALL)\n"
                        "text = re.sub(r\"<style[^>]*>.*?</style>\", \"\", text, flags=re.DOTALL)\n"
                        "text = re.sub(r\"<[^>]+>\", \" \", text)\n"
                        "text = re.sub(r\"\\s+\", \" \", text).strip()\n"
                        "\n"
                        "title_match = re.search(r\"<title[^>]*>(.*?)</title>\", html, re.IGNORECASE | re.DOTALL)\n"
                        "title = title_match.group(1).strip() if title_match else url\n"
                        "\n"
                        "max_chars = 6000\n"
                        "truncated = len(text) > max_chars\n"
                        "if truncated:\n"
                        "    text = text[:max_chars]\n"
                        "\n"
                        "return {\n"
                        "    \"page_title\": title,\n"
                        "    \"page_text\": text,\n"
                        "    \"page_url\": url,\n"
                        "    \"page_length\": len(response.text),\n"
                        "    \"truncated\": truncated,\n"
                        "}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "llm",
                "position": {"x": 80, "y": 260},
                "data": {
                    "name": "summarize_page",
                    "model": "claude-haiku",
                    "prompt": (
                        "You are a research assistant. Summarize this web page concisely.\n"
                        "\n"
                        "Title: {page_title}\n"
                        "URL: {page_url}\n"
                        "\n"
                        "Content:\n"
                        "{page_text}\n"
                        "\n"
                        "Provide:\n"
                        "1. A 2-3 sentence summary\n"
                        "2. Key points (3-5 bullet points)\n"
                        "3. The primary topic/category\n"
                        "\n"
                        "Return as JSON with keys: \"summary\", \"key_points\" (list), \"category\"."
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
        ],
    },
}


EXAMPLE_SEEDS = [
    CODE_REVIEWER,
    CSV_ANALYZER,
    EMAIL_DRAFTER,
    GIT_CHANGELOG,
    LOG_ANALYZER,
    MULTI_MODEL_DEBATE,
    PROCESS_MANAGER,
    RESEARCH_PIPELINE,
    RUN_AND_ANALYZE,
    WEB_SCRAPER_SUMMARIZER,
]
