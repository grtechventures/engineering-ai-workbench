# Direct skill and package authoring

Skills library now supports **Create skill** and **Import skill** without a prior analysis. Import UTF-8 Markdown/text instructions or the Workbench JSON format below, up to 16 KB. Markdown is retained as reference text, including any front matter; this is not a compatibility claim for another agent's skill format. Imports populate the editable form before saving a candidate. Optional Python is parsed for syntax but never executed during import or release.

```json
{
  "name": "Summary statistics",
  "description": "Report mean and population standard deviation",
  "instructions": "Calculate the mean and population standard deviation for each provided series; label units and assumptions.",
  "tools": ["python.reviewed_extension"],
  "code": ""
}
```

Review the candidate's instructions and optional reference code, then approve release. Assign it to an enabled local-model agent in Agents. Back in Skills library, select that agent and optionally a completed analysis result, then choose **Prepare Python task**. Without an analysis, the instructions must supply the necessary values. The local model drafts a script using the skill as guidance; optional reference code is not guaranteed to be copied verbatim. Review the actual script before Docker execution and review its outputs afterward.

Agent permissions, skill release status and containing package status are rechecked before execution. Retiring a skill or disabling its package blocks new execution, including already-prepared tasks. Existing artifacts remain readable. Revisions preserve skill provenance. Authored skills cannot silently become comparison recipes and cannot be scheduled unattended. There is no signature verification, collaborative release workflow or in-place skill editing yet; create a new draft and retire the previous skill when replacing it.

## Plugin packages

Plugins offers **Add plugin package** for pasted Workbench JSON and **Import package** for a JSON file. The supported package is declarative: a name, description and one to ten skill definitions. It does not install native code, arbitrary ZIP archives, third-party MCP servers or UI extensions.

```json
{
  "name": "Team statistics",
  "description": "Reusable numerical methods",
  "skills": [
    {
      "name": "Mean calculation",
      "instructions": "Calculate the arithmetic mean of the supplied values.",
      "tools": ["python.reviewed_extension"]
    }
  ]
}
```

Saving creates a package candidate and skill candidates atomically. Review the included skills in Skills library, enable the package, and release the desired skills separately. Disabling a package blocks its skills from new execution. Runtime permissions do not expand on import.

## Tools

The Tools form supports repeated registration: save one entry, then enter the next. Multiple application/module references and source-folder references are retained. They remain metadata awaiting adapter integration, not executable capabilities. Unknown tool identifiers in skill imports are rejected.
