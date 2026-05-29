import { useMemo, useState } from "react";

import { createProject, requestSuggestion, updateBlock } from "./api";
import "./App.css";
import { statusLabel } from "./statusLabels";
import type { BlockStatus, ProjectState, TextBlock } from "./types";

type Direction = "en_to_zh" | "zh_to_en";

export default function App() {
  const [enFile, setEnFile] = useState<File | null>(null);
  const [zhFile, setZhFile] = useState<File | null>(null);
  const [project, setProject] = useState<ProjectState | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [draftEn, setDraftEn] = useState("");
  const [draftZh, setDraftZh] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [suggestionTarget, setSuggestionTarget] = useState<TextBlock | null>(null);
  const [direction, setDirection] = useState<Direction>("en_to_zh");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const selectedPair = useMemo(() => {
    if (!project) return null;
    const pair = project.mappings[selectedIndex];
    return {
      en: project.enBlocks.find((block) => block.id === pair?.enId) ?? null,
      zh: project.zhBlocks.find((block) => block.id === pair?.zhId) ?? null,
      mapped: pair?.mapped ?? false,
    };
  }, [project, selectedIndex]);

  async function parseDocuments() {
    if (!enFile || !zhFile) {
      setMessage("请先上传英文 Word 和中文 Word。");
      return;
    }
    setBusy(true);
    try {
      const created = await createProject(enFile, zhFile);
      setProject(created);
      setSelectedIndex(0);
      setDraftEn("");
      setDraftZh("");
      setMessage(created.warnings[0] ?? "文档解析完成。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文档解析失败。");
    } finally {
      setBusy(false);
    }
  }

  function selectPair(index: number) {
    if (!project) return;
    const pair = project.mappings[index];
    const en = project.enBlocks.find((block) => block.id === pair.enId);
    const zh = project.zhBlocks.find((block) => block.id === pair.zhId);
    setSelectedIndex(index);
    setDraftEn(en?.text ?? "");
    setDraftZh(zh?.text ?? "");
    setSuggestion("");
    setSuggestionTarget(null);
  }

  function replaceProjectBlock(
    current: ProjectState,
    blockId: string,
    text: string,
    status: BlockStatus,
  ): ProjectState {
    return {
      ...current,
      enBlocks: current.enBlocks.map((block) => (block.id === blockId ? { ...block, text, status } : block)),
      zhBlocks: current.zhBlocks.map((block) => (block.id === blockId ? { ...block, text, status } : block)),
    };
  }

  async function sync(nextDirection: Direction) {
    if (!project || !selectedPair?.en || !selectedPair.zh || !selectedPair.mapped) {
      setMessage("当前段落未建立映射，无法同步。");
      return;
    }
    setBusy(true);
    setDirection(nextDirection);
    try {
      const source = nextDirection === "en_to_zh" ? selectedPair.en : selectedPair.zh;
      const target = nextDirection === "en_to_zh" ? selectedPair.zh : selectedPair.en;
      const sourceText = nextDirection === "en_to_zh" ? draftEn : draftZh;
      const targetText = nextDirection === "en_to_zh" ? draftZh : draftEn;
      await updateBlock({
        projectId: project.projectId,
        blockId: source.id,
        text: sourceText,
        status: "modified",
      });
      setProject(replaceProjectBlock(project, source.id, sourceText, "modified"));
      const nextSuggestion = await requestSuggestion({
        projectId: project.projectId,
        direction: nextDirection,
        sourceBlockId: source.id,
        targetBlockId: target.id,
        sourceText,
        targetText,
      });
      setSuggestion(nextSuggestion);
      setSuggestionTarget(target);
      setMessage("已生成同步建议，请确认后写回。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "同步建议生成失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  async function confirmSuggestion() {
    if (!project || !suggestionTarget) return;
    await updateBlock({
      projectId: project.projectId,
      blockId: suggestionTarget.id,
      text: suggestion,
      status: "modified",
    });
    setProject(replaceProjectBlock(project, suggestionTarget.id, suggestion, "modified"));
    if (suggestionTarget.side === "en") setDraftEn(suggestion);
    if (suggestionTarget.side === "zh") setDraftZh(suggestion);
    setSuggestion("");
    setSuggestionTarget(null);
    setMessage("已确认写回。");
  }

  function renderBlock(block: TextBlock | null, index: number, language: "英文" | "中文") {
    if (!block) {
      return (
        <button type="button" className="block-row unmapped" disabled key={`${language}-${index}-unmapped`}>
          <span>{language}段落 {index + 1}</span>
          <span>未映射</span>
        </button>
      );
    }

    return (
      <button
        type="button"
        className={`block-row ${selectedIndex === index ? "selected" : ""}`}
        onClick={() => selectPair(index)}
        key={block.id}
      >
        <span className="block-index">{language} {index + 1}</span>
        <span className="block-preview">{block.text}</span>
        <span className="status-pill">{statusLabel[block.status]}</span>
      </button>
    );
  }

  return (
    <main className="app-shell">
      <header className="toolbar">
        <label className="file-button">
          上传英文 Word
          <input
            aria-label="上传英文 Word"
            type="file"
            accept=".docx"
            onChange={(event) => setEnFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <label className="file-button">
          上传中文 Word
          <input
            aria-label="上传中文 Word"
            type="file"
            accept=".docx"
            onChange={(event) => setZhFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="button" onClick={parseDocuments} disabled={busy}>
          解析文档
        </button>
        <button type="button" disabled={!project || busy}>
          导出更新后的 Word
        </button>
      </header>

      {message && <div className="message">{message}</div>}

      <section className="editor-grid">
        <article className="panel">
          <h2>英文原稿</h2>
          <div className="block-list">
            {project ? (
              project.mappings.map((pair, index) =>
                renderBlock(project.enBlocks.find((block) => block.id === pair.enId) ?? null, index, "英文"),
              )
            ) : (
              <p className="empty">请先上传并解析英文 Word。</p>
            )}
          </div>
          <label className="editor-label" htmlFor="en-editor">
            英文段落内容
          </label>
          <textarea
            id="en-editor"
            value={draftEn}
            onChange={(event) => setDraftEn(event.target.value)}
            disabled={!selectedPair?.en}
          />
          <button type="button" onClick={() => sync("en_to_zh")} disabled={!selectedPair?.mapped || busy}>
            同步到中文
          </button>
        </article>

        <article className="panel">
          <h2>中文原稿</h2>
          <div className="block-list">
            {project ? (
              project.mappings.map((pair, index) =>
                renderBlock(project.zhBlocks.find((block) => block.id === pair.zhId) ?? null, index, "中文"),
              )
            ) : (
              <p className="empty">请先上传并解析中文 Word。</p>
            )}
          </div>
          <label className="editor-label" htmlFor="zh-editor">
            中文段落内容
          </label>
          <textarea
            id="zh-editor"
            value={draftZh}
            onChange={(event) => setDraftZh(event.target.value)}
            disabled={!selectedPair?.zh}
          />
          <button type="button" onClick={() => sync("zh_to_en")} disabled={!selectedPair?.mapped || busy}>
            同步到英文
          </button>
        </article>
      </section>

      <section className="suggestion-panel">
        <h2>同步建议</h2>
        <p>{direction === "en_to_zh" ? "当前方向：英文同步到中文" : "当前方向：中文同步到英文"}</p>
        <textarea
          aria-label="同步建议内容"
          value={suggestion}
          onChange={(event) => setSuggestion(event.target.value)}
          placeholder="生成同步建议后会显示在这里。"
        />
        <button type="button" onClick={confirmSuggestion} disabled={!suggestionTarget || !suggestion || busy}>
          确认写回
        </button>
      </section>
    </main>
  );
}
