/* Calibre-Web UI Phase-8: Batch selection + batch action bar (Alpine).
 * 依赖 Alpine。纯前端：复用现有 edit-book/shelf 后端 JSON 端点，不改后端。
 * 每个书库书卡挂 .batch-checkbox（value=book id），本组件维护 selected 数组。
 */
function calibreBatch(editUrl, delUrl) {
  return {
    selected: [],
    editKind: 'tags',
    value: '',
    text: { tags: '', series: '', authors: '' },
    busy: false,
    confirmingDelete: false,
    feedback: { kind: '', text: '' },

    get count() { return this.selected.length; },

    isAllSelected() {
      const boxes = document.querySelectorAll('.batch-checkbox');
      return boxes.length > 0 && this.selected.length === boxes.length;
    },

    toggleAll() {
      const boxes = document.querySelectorAll('.batch-checkbox');
      if (this.isAllSelected()) {
        this.selected = [];
      } else {
        this.selected = Array.from(boxes).map((b) => String(b.value));
      }
    },

    clear() {
      this.selected = [];
      this.confirmingDelete = false;
      this.feedback = { kind: '', text: '' };
    },

    setFeedback(kind, text) {
      this.feedback = { kind, text };
      window.setTimeout(() => { this.feedback = { kind: '', text: '' }; }, 3000);
    },

    async doEdit() {
      if (this.count === 0) return;
      const val = (this.value || '').trim();
      if (!this.text[this.editKind] && !val) {
        this.setFeedback('error', this.textEmpty());
        return;
      }
      const body = {
        pk: this.selected.map(Number),
        value: val || null,
        multi: 'True',
      };
      this.busy = true;
      try {
        const res = await fetch(editUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (data && data.length) {
          const ok = data.every((r) => r && r.success === true);
          this.setFeedback(ok ? 'success' : 'error', ok ? this.textOk() : this.textFail());
        } else {
          this.setFeedback('success', this.textOk());
        }
        this.clear();
      } catch (e) {
        this.setFeedback('error', this.textFail());
      } finally {
        this.busy = false;
      }
    },

    async doDelete() {
      if (this.count === 0) return;
      this.busy = true;
      try {
        const res = await fetch(delUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bookid: this.selected.map(Number) }),
        });
        if (res.ok) this.setFeedback('success', this.textDeleted());
        else this.setFeedback('error', this.textFail());
        this.clear();
      } catch (e) {
        this.setFeedback('error', this.textFail());
      } finally {
        this.busy = false;
        this.confirmingDelete = false;
      }
    },

    /* i18n（由 layout 注入，缺省英文） */
    textOk() { return window.calibreBatchT ? window.calibreBatchT.ok : 'Changes applied'; },
    textFail() { return window.calibreBatchT ? window.calibreBatchT.fail : 'Request failed'; },
    textEmpty() { return window.calibreBatchT ? window.calibreBatchT.empty : 'Enter a value'; },
    textDeleted() { return window.calibreBatchT ? window.calibreBatchT.deleted : 'Books deleted'; },
  };
}
