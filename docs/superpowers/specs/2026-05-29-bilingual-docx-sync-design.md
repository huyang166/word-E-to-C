# Bilingual DOCX Sync Local Prototype Design

## Goal

Build a local web prototype for Chinese-speaking manuscript editors. The user uploads an English Word manuscript and a Chinese Word manuscript, edits either language in a side-by-side web interface, asks an OpenAI or OpenAI-compatible model to generate the corresponding paragraph in the other language, confirms the suggestion, and exports updated DOCX files while preserving the original Word structure as much as possible.

## Scope

### In Scope

- Local web application.
- English DOCX and Chinese DOCX upload.
- DOCX parsing for body paragraphs, headings, and table-cell paragraphs.
- Order-based paragraph mapping between the two files.
- Side-by-side bilingual editor.
- Bidirectional synchronization:
  - English edit generates Chinese suggestion.
  - Chinese edit generates English suggestion.
- Manual confirmation before writing generated text to the paired document.
- Paragraph-level DOCX write-back.
- Updated DOCX export for both languages.
- Simplified Chinese user interface, including labels, buttons, status text, and error messages.
- OpenAI API and OpenAI-compatible API configuration through environment variables.

### Out of Scope for v1

- Semantic synchronization of equations, images, charts, text boxes, footnotes, endnotes, captions, cross references, and complex field codes.
- Automatic alignment repair for heavily mismatched manuscripts.
- Multi-user collaboration.
- Login, cloud storage, project history, or version history.
- Full preservation of inline run-level formatting inside replaced text when a paragraph contains complex mixed formatting.

## Recommended Architecture

Use a Python backend and React frontend:

- Backend: FastAPI.
- DOCX processing: parse and modify DOCX package/XML with Python tooling, using `python-docx` where it helps and direct XML access where needed.
- Frontend: React + Vite.
- API provider: OpenAI-compatible chat/text generation endpoint configured by environment variables.

This architecture keeps DOCX manipulation in Python, where Word XML tooling is mature, while React provides a practical editing interface.

## User Workflow

1. User opens the local web page.
2. User uploads the English Word file and Chinese Word file.
3. User clicks `解析文档`.
4. Backend extracts editable text blocks from both files.
5. Backend maps English and Chinese blocks by order.
6. Frontend shows a side-by-side bilingual editor.
7. User selects a mapped paragraph pair.
8. User edits either the English or Chinese text.
9. User clicks `同步到中文` or `同步到英文`.
10. Backend calls the configured model and returns a suggested replacement for the paired paragraph.
11. User reviews or manually edits the suggestion.
12. User clicks `确认写回`.
13. Frontend marks the target paragraph as confirmed.
14. User exports updated DOCX files.

## DOCX Text Block Model

The backend exposes parsed document text as text blocks:

```json
{
  "id": "en-00042",
  "side": "en",
  "kind": "paragraph",
  "index": 42,
  "text": "Original paragraph text...",
  "mappedId": "zh-00042",
  "status": "clean"
}
```

Supported `kind` values in v1:

- `paragraph`: ordinary body paragraph.
- `heading`: heading paragraph.
- `table_cell`: paragraph inside a table cell.
- `unsupported`: detected but not editable in v1.

The initial mapper assumes the two manuscripts have the same editable text-block order. If counts differ, the app maps up to the shorter length and marks extra blocks as unmapped.

## DOCX Write-Back Strategy

The backend stores the uploaded DOCX files as base documents. Export does not rebuild a new manuscript from scratch. Instead, it opens the original DOCX package and performs minimal text replacement on mapped blocks.

Rules:

1. Preserve the original DOCX package and XML structure.
2. Preserve paragraph styles, heading styles, tables, numbering, images, equations, page settings, headers, footers, and other non-target structures where possible.
3. Locate the target paragraph or table-cell paragraph by its parsed block path.
4. Replace only text content in that block.
5. If the target block has one or more text runs, write the replacement text into the first text run and clear later text-run content in the same block.
6. If the target block has no writable text run and the user confirms a non-empty replacement, create a minimal text run in that block.
7. Do not attempt to preserve complex inline formatting inside a replaced paragraph in v1.

This approach is optimized for manuscript text, headings, simple tables, numbering, and paragraph styles. It intentionally avoids complex Word features that need specialized handling.

## AI Synchronization Strategy

The backend owns model calls so the API key is never exposed to the browser.

Configuration:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=...
```

If the user uses an OpenAI-compatible provider, they can change `OPENAI_BASE_URL` and `OPENAI_MODEL`.

For English-to-Chinese sync, the model receives:

- Direction: `en_to_zh`.
- Modified English paragraph.
- Current mapped Chinese paragraph.
- Instruction to write a faithful Chinese manuscript-style replacement that reflects only the English change.

For Chinese-to-English sync, the model receives:

- Direction: `zh_to_en`.
- Modified Chinese paragraph.
- Current mapped English paragraph.
- Instruction to write a faithful English manuscript-style replacement that reflects only the Chinese change.

The model should return only the suggested paragraph text. It should not add explanations, markdown, citations, or unrelated content.

Failure behavior:

- Missing API key: show a Simplified Chinese configuration error.
- Model request failure: keep current edits, do not write back.
- Empty model output: show retry guidance.
- User does not confirm: do not modify the paired document.

## Frontend Design

Use the side-by-side layout selected by the user.

Main areas:

- Top toolbar:
  - `上传英文 Word`
  - `上传中文 Word`
  - `解析文档`
  - `导出更新后的 Word`
- Left panel:
  - English paragraph list.
  - English selected paragraph editor.
- Right panel:
  - Chinese paragraph list.
  - Chinese selected paragraph editor.
- Suggestion area:
  - Current mapping information.
  - Sync direction.
  - AI suggestion preview.
  - Editable suggestion field.
  - `确认写回`.

All user-facing interface text must be Simplified Chinese. Internal status values may remain English for code clarity, but the UI must map them to Chinese labels.

Status labels:

| Internal value | Chinese label |
| --- | --- |
| `clean` | `未修改` |
| `edited` | `已编辑，待同步` |
| `suggested` | `有同步建议，待确认` |
| `modified` | `已确认写回` |
| `error` | `处理失败` |

Example user-facing messages:

- `未配置 API Key，请在 .env 中设置。`
- `两份文档段落数量不一致，系统已按顺序建立可用映射。`
- `同步建议生成失败，请稍后重试。`
- `请先上传英文 Word 和中文 Word。`

## Data Flow

1. `POST /api/projects`
   - Accepts English and Chinese DOCX files.
   - Stores originals in a local working directory.
   - Parses text blocks.
   - Builds order-based mapping.
   - Returns project id, text blocks, mapping, and warnings.

2. `POST /api/projects/{project_id}/suggest`
   - Accepts source block id, target block id, direction, source text, and current target text.
   - Calls configured model.
   - Returns suggestion text.

3. `PATCH /api/projects/{project_id}/blocks/{block_id}`
   - Updates the in-memory or local project state for a block after the user edits or confirms text.

4. `POST /api/projects/{project_id}/export`
   - Applies confirmed block replacements to the original DOCX files.
   - Returns downloadable updated English and Chinese DOCX files.

## Error Handling

- Invalid file type: reject files that are not `.docx`.
- Corrupt DOCX: show a parse failure message and preserve uploaded file state for retry.
- Block count mismatch: warn but proceed with shortest-length mapping.
- Unmapped block selected: allow viewing and editing locally, but disable sync until mapped.
- Unsupported content: preserve it in export and label it as unsupported where visible.
- API failure: show the provider error summary in Chinese without leaking secrets.

## Testing Strategy

Backend tests:

- Parse ordinary paragraphs from a DOCX.
- Parse headings.
- Parse table-cell paragraphs.
- Build order-based mappings.
- Warn on mismatched block counts.
- Replace a paragraph while preserving surrounding DOCX structure.
- Replace a table-cell paragraph.
- Preserve non-target paragraphs during export.
- Reject non-DOCX uploads.
- Handle missing API key without calling a provider.
- Call an injectable model client for bidirectional suggestions.

Frontend tests:

- Show upload controls in Simplified Chinese.
- Render mapped paragraphs side by side.
- Display Chinese status labels.
- Enable `同步到中文` after editing English.
- Enable `同步到英文` after editing Chinese.
- Show suggestion without auto-applying it.
- Apply suggestion only after `确认写回`.
- Show mapping mismatch warnings in Chinese.

Manual verification:

- Upload two simple paired DOCX files.
- Edit an English paragraph, generate Chinese suggestion, confirm, export, and inspect the Chinese DOCX formatting.
- Edit a Chinese paragraph, generate English suggestion, confirm, export, and inspect the English DOCX formatting.
- Verify tables and numbering remain usable.
- Verify images and equations remain present.

## Implementation Notes

- Keep project files local under a generated project id.
- Do not expose provider keys to frontend code.
- Treat AI output as a suggestion until the user explicitly confirms it.
- Prefer simple paragraph-order mapping for v1.
- Keep the UI dense, practical, and document-work focused rather than marketing-like.
- Do not add cloud features or collaboration until the local prototype is reliable.
