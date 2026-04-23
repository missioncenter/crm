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

  const renderUpdatedAt = () => {
    if (!updatedAt) return;
    const now = new Date();
    updatedAt.textContent = "Updated " + now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

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
        feedContainer.innerHTML = data.feed_html;
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
  renderUpdatedAt();
  window.setInterval(refreshFeed, 60000);
}

function createSortable(columnElement) {
  Sortable.create(columnElement, {
    group: "shared",
    animation: 150,
    ghostClass: "task-card--ghost",
    chosenClass: "task-card--chosen",
    dragClass: "task-card--dragging",
    onEnd: function (event) {
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

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".task-list").forEach((column) => createSortable(column));
  syncProgressBars();
  bindProgressSlider();
  bindActivityFeed();

  const commentForm = document.getElementById("task-comment-form");
  const commentsList = document.getElementById("task-comments-list");
  const commentCount = document.getElementById("task-comment-count");
  if (commentForm && commentsList) {
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
          showToast("Comment posted.", true);
        })
        .catch(() => showToast("Unable to post comment.", false));
    });
  }
});
