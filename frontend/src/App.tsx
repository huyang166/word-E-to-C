import "./App.css";

export default function App() {
  return (
    <main className="app-shell">
      <header className="toolbar">
        <label className="file-button">
          上传英文 Word
          <input type="file" accept=".docx" />
        </label>
        <label className="file-button">
          上传中文 Word
          <input type="file" accept=".docx" />
        </label>
        <button type="button">解析文档</button>
        <button type="button">导出更新后的 Word</button>
      </header>
      <section className="editor-grid">
        <article className="panel">
          <h2>英文原稿</h2>
          <p className="empty">请先上传并解析英文 Word。</p>
        </article>
        <article className="panel">
          <h2>中文原稿</h2>
          <p className="empty">请先上传并解析中文 Word。</p>
        </article>
      </section>
      <section className="suggestion-panel">
        <h2>同步建议</h2>
        <p>选择一组对应段落后，可以生成并确认另一侧的同步建议。</p>
      </section>
    </main>
  );
}
