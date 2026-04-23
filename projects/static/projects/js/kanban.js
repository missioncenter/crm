function getCookie(name) {
  const cookies = document.cookie.split(";").map((item) => item.trim());
  const cookie = cookies.find((item) => item.startsWith(name + "="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
}

const csrfToken = getCookie("csrftoken");

function showToast(message, ok) {
  let toast = document.getElementById("kanban-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "kanban-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = "kanban-toast " + (ok ? "kanban-toast--ok" : "kanban-toast--err");
  toast.classList.add("kanban-toast--visible");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("kanban-toast--visible"), 2500);
}

function updateBadge(list) {
  const badge = list.closest(".kanban-column").querySelector(".badge");
  if (badge) badge.textContent = list.querySelectorAll(".task-card").length;
}

function updateEmptyState(list) {
  const hasCards = list.querySelectorAll(".task-card").length > 0;
  const existing = list.querySelector(".empty-state");
  if (hasCards && existing) existing.remove();
  if (!hasCards && !existing) {
    const el = document.createElement("div");
    el.className = "empty-state";
    el.textContent = "No tasks";
    list.appendChild(el);
  }
}

function updateTaskStatus(taskId, status) {
  const formData = new FormData();
  formData.append("task_id", taskId);
  formData.append("status", status);

  return fetch("/tasks/update-status/", {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
    body: formData,
  }).then((response) => response.json());
}

function getColumnLabel(status) {
  const labels = { ToDo: "To Do", InProgress: "In Progress", Review: "Review", Done: "Done" };
  return labels[status] || status;
}

function syncProgressBars() {
  document.querySelectorAll("[data-task-progress-widget]").forEach((widget) => {
    const progress = Number(widget.dataset.progress || 0);
    const fill = widget.querySelector("[data-task-progress-fill]");
    if (fill) {
      fill.style.width = Math.max(0, Math.min(100, progress)) + "%";
    }
  });
}

function bindProgressSlider() {
  const slider = document.querySelector("[data-task-progress-slider]");
  const form = document.getElementById("task-progress-form");
  const valueBadge = document.getElementById("task-progress-value");
  const inlineValue = document.querySelector("[data-task-progress-inline-value]");
  const widget = document.querySelector("[data-task-progress-widget]");
  const fill = document.querySelector("[data-task-progress-fill]");
  if (!slider || !form || !widget) return;

  const updateUi = (value) => {
    const normalized = Math.max(0, Math.min(100, Number(value) || 0));
    widget.dataset.progress = String(normalized);
    if (fill) fill.style.width = normalized + "%";
    if (valueBadge) valueBadge.textContent = normalized + "%";
    if (inlineValue) inlineValue.textContent = normalized + "%";
  };

  let pendingSave = null;
  const saveProgress = (value) => {
    const formData = new FormData(form);
    formData.set("progress", String(value));
    return fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.ok) {
          showToast(data.error || "Unable to update progress.", false);
          updateUi(slider.value);
          return;
        }
        updateUi(data.progress);
        showToast("Progress updated.", true);
      })
      .catch(() => showToast("Unable to update progress.", false));
  };

  slider.addEventListener("input", () => updateUi(slider.value));
  slider.addEventListener("change", () => {
    updateUi(slider.value);
    clearTimeout(pendingSave);
    pendingSave = setTimeout(() => saveProgress(slider.value), 150);
  });
}

function bindActivityFeed() {
  const root = document.querySelector("[data-activity-feed-root]");
  if (!root) return;

  const refreshButton = root.querySelector("[data-activity-feed-refresh]");
  const updatedAt = root.querySelector("[data-activity-feed-updated-at]");
  const feedContainer = document.getElementById("global-activity-feed");
  const feedUrl = root.dataset.activityFeedUrl;
  let feedList = root.querySelector("[data-activity-feed-list]");
  let feedSentinel = root.querySelector("[data-activity-feed-sentinel]");
  let feedLoading = root.querySelector("[data-activity-feed-loading]");
  let nextOffset = Number(root.dataset.activityFeedNextOffset || (feedList ? feedList.children.length : 0));
  let hasMore = root.dataset.activityFeedHasMore === "true";
  let loadingMore = false;
  let observer = null;

  const renderUpdatedAt = () => {
    if (!updatedAt) return;
    const now = new Date();
    updatedAt.textContent = "Updated " + now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const syncState = () => {
    feedList = root.querySelector("[data-activity-feed-list]");
    feedSentinel = root.querySelector("[data-activity-feed-sentinel]");
    feedLoading = root.querySelector("[data-activity-feed-loading]");
    if (!feedList) return;
    root.dataset.activityFeedNextOffset = String(nextOffset);
    root.dataset.activityFeedHasMore = hasMore ? "true" : "false";
    if (observer) observer.disconnect();
    if (feedSentinel && hasMore) {
      observer.observe(feedSentinel);
    }
  };

  const setLoading = (isLoading) => {
    if (feedLoading) {
      feedLoading.classList.toggle("hidden", !isLoading);
    }
  };

  const replaceFeed = (html, emptyHtml, newHasMore, newNextOffset) => {
    if (!feedContainer) return;
    feedContainer.innerHTML = html || emptyHtml || "";
    nextOffset = Number(newNextOffset || 0);
    hasMore = Boolean(newHasMore);
    syncState();
  };

  const appendFeed = (html, newHasMore, newNextOffset) => {
    if (!feedList) return;
    if (html) {
      feedList.insertAdjacentHTML("beforeend", html);
    }
    nextOffset = Number(newNextOffset || nextOffset);
    hasMore = Boolean(newHasMore);
    syncState();
  };

  const loadMore = () => {
    if (!feedUrl || !feedContainer || loadingMore || !hasMore) return Promise.resolve();
    loadingMore = true;
    setLoading(true);
    const url = new URL(feedUrl, window.location.origin);
    url.searchParams.set("mode", "append");
    url.searchParams.set("offset", String(nextOffset));
    url.searchParams.set("limit", "20");
    return fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((response) => response.json())
      .then((data) => {
        if (!data.ok) {
          showToast(data.error || "Unable to load more activity.", false);
          return;
        }
        appendFeed(data.feed_html, data.has_more, data.next_offset);
      })
      .catch(() => showToast("Unable to load more activity.", false))
      .finally(() => {
        loadingMore = false;
        setLoading(false);
      });
  };

  observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      loadMore();
    }
  }, { root: null, rootMargin: "200px 0px" });

  syncState();

  const refreshFeed = () => {
    if (!feedUrl || !feedContainer) return Promise.resolve();
    if (refreshButton) refreshButton.disabled = true;
    return fetch(feedUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((response) => response.json())
      .then((data) => {
        if (!data.ok) {
          showToast(data.error || "Unable to refresh activity feed.", false);
          return;
        }
        replaceFeed(data.feed_html, data.empty_html, data.has_more, data.next_offset);
        renderUpdatedAt();
      })
      .catch(() => showToast("Unable to refresh activity feed.", false))
      .finally(() => {
        if (refreshButton) refreshButton.disabled = false;
      });
  };

  if (refreshButton) {
    refreshButton.addEventListener("click", refreshFeed);
  }
  if (feedSentinel && hasMore) {
    observer.observe(feedSentinel);
  }
  renderUpdatedAt();
  window.setInterval(refreshFeed, 60000);
}

function bindWysiwygEditors() {
  const editors = document.querySelectorAll("[data-wysiwyg-field]");
  if (!editors.length) return;

  const exec = (command, value = null) => {
    document.execCommand(command, false, value);
  };

  const sanitizeHtml = (html) => {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html || "";
    wrapper.querySelectorAll("script, style, iframe, object, embed").forEach((node) => node.remove());
    wrapper.querySelectorAll("a").forEach((link) => {
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");
    });
    return wrapper.innerHTML;
  };

  editors.forEach((field) => {
    const editor = field.querySelector("[data-wysiwyg-editor]");
    const textarea = field.querySelector("textarea[data-wysiwyg-textarea]");
    const toolbar = field.querySelector("[data-wysiwyg-toolbar]");
    if (!editor || !textarea) return;

    editor.innerHTML = textarea.value || "";

    const syncToTextarea = () => {
      textarea.value = sanitizeHtml(editor.innerHTML.trim());
    };

    editor.addEventListener("input", syncToTextarea);
    editor.addEventListener("keyup", syncToTextarea);
    editor.addEventListener("paste", () => window.setTimeout(syncToTextarea, 0));
    editor.addEventListener("cut", () => window.setTimeout(syncToTextarea, 0));
    editor.addEventListener("drop", () => window.setTimeout(syncToTextarea, 0));
    editor.addEventListener("compositionend", syncToTextarea);
    editor.addEventListener("blur", syncToTextarea);

    if (toolbar) {
      toolbar.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-wysiwyg-command]");
        if (!button) return;
        event.preventDefault();
        editor.focus();
        const command = button.dataset.wysiwygCommand;
        if (command === "createLink") {
          const currentSelection = window.getSelection();
          const selectedText = currentSelection ? currentSelection.toString().trim() : "";
          const url = window.prompt("Enter a link URL", "https://");
          if (!url) return;
          exec(command, url.trim());
          if (!selectedText) {
            syncToTextarea();
          }
        } else {
          exec(command);
        }
        syncToTextarea();
      });
    }

    const form = textarea.closest("form");
    if (form) {
      form.addEventListener("submit", () => syncToTextarea());
      form.addEventListener("formdata", () => syncToTextarea());
    }

    syncToTextarea();
  });
}

function createSortable(columnElement) {
  Sortable.create(columnElement, {
    group: "shared",
    animation: 150,
    ghostClass: "task-card--ghost",
    chosenClass: "task-card--chosen",
    dragClass: "task-card--dragging",
    onStart: function () {
      window.__kanbanDragging = true;
    },
    onEnd: function (event) {
      window.__kanbanDragging = false;
      const fromList = event.from;
      const toList = event.to;

      // Dropped back into same column — nothing to do
      if (fromList === toList) return;

      const taskId = event.item.dataset.taskId;
      const newStatus = toList.dataset.status;

      // Immediately update card color attribute
      event.item.dataset.status = newStatus;

      // Update badges and empty-states right away
      updateBadge(fromList);
      updateBadge(toList);
      updateEmptyState(fromList);
      updateEmptyState(toList);

      // Persist to server
      updateTaskStatus(taskId, newStatus).then((data) => {
        if (data.ok) {
          if (data.overdue) event.item.classList.add("overdue");
          else event.item.classList.remove("overdue");
          showToast("Moved to \"" + getColumnLabel(newStatus) + "\"", true);
        } else {
          showToast(data.error || "Unable to update task status.", false);
          // Revert DOM
          event.item.dataset.status = fromList.dataset.status;
          fromList.appendChild(event.item);
          updateBadge(fromList);
          updateBadge(toList);
          updateEmptyState(fromList);
          updateEmptyState(toList);
        }
      });
    },
  });
}

function bindTaskCardNavigation() {
  document.querySelectorAll(".task-card[data-task-url]").forEach((card) => {
    const openCard = () => {
      const url = card.dataset.taskUrl;
      if (url) window.location.href = url;
    };

    card.addEventListener("click", (event) => {
      if (window.__kanbanDragging) return;
      if (event.target.closest("a, button, input, textarea, select, [contenteditable='true']")) return;
      openCard();
    });

    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openCard();
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".task-list").forEach((column) => createSortable(column));
  bindTaskCardNavigation();
  syncProgressBars();
  bindProgressSlider();
  bindActivityFeed();
  bindWysiwygEditors();

  const commentForm = document.getElementById("task-comment-form");
  const commentsList = document.getElementById("task-comments-list");
  const commentCount = document.getElementById("task-comment-count");
  if (commentForm && commentsList) {
    const commentEditor = commentForm.querySelector("[data-wysiwyg-editor]");
    const commentTextarea = commentForm.querySelector("textarea[data-wysiwyg-textarea]");
    commentForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(commentForm);

      fetch(commentForm.action, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (!data.ok) {
            showToast(data.error || "Unable to post comment.", false);
            return;
          }
          commentsList.innerHTML = data.comments_html;
          if (commentCount) {
            commentCount.textContent = String(commentsList.querySelectorAll(".task-comment-item").length);
          }
          commentForm.reset();
          if (commentEditor) {
            commentEditor.innerHTML = "";
          }
          if (commentTextarea) {
            commentTextarea.value = "";
          }
          showToast("Comment posted.", true);
        })
        .catch(() => showToast("Unable to post comment.", false));
    });
  }
});
